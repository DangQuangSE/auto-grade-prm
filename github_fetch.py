"""Fetch a GitHub repository snapshot over HTTPS (no git binary required).

Downloads a tarball via GitHub's codeload service and extracts it into a
caller-supplied directory. Designed to work on read-only, git-less runtimes
such as Vercel serverless functions, where only ``/tmp`` is writable and
``subprocess``-based ``git clone`` is not available.
"""
import os
import re
import tarfile
import urllib.error
import urllib.request
from urllib.parse import quote

MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # 100MB extracted size cap
MAX_FILES = 20000
API_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 60
USER_AGENT = "flutter-auto-grader"

_SSH_RE = re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?/?$")
_HTTPS_RE = re.compile(
    r"^https?://(www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?"
    r"(/(tree|blob)/(?P<ref>[^/]+))?(/.*)?$"
)


class GithubFetchError(Exception):
    """Raised for any recoverable failure while fetching a GitHub repo."""


def parse_github_url(url: str):
    """Return (owner, repo, ref_or_None) parsed from a GitHub URL."""
    url = url.strip()
    match = _SSH_RE.match(url) or _HTTPS_RE.match(url)
    if not match:
        raise GithubFetchError("Không nhận diện được owner/repo từ URL GitHub.")
    return match.group("owner"), match.group("repo"), match.groupdict().get("ref")


def _github_api_get(path: str, token: str = None):
    url = f"https://api.github.com{path}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            import json

            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GithubFetchError("Không tìm thấy repository trên GitHub (repo private hoặc không tồn tại).") from exc
        if exc.code == 403:
            raise GithubFetchError("GitHub API từ chối yêu cầu (có thể do giới hạn tần suất truy cập).") from exc
        raise GithubFetchError(f"Lỗi khi truy vấn GitHub API (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise GithubFetchError(f"Lỗi kết nối tới GitHub API: {exc.reason}") from exc


def resolve_ref(owner: str, repo: str, ref: str = None, token: str = None) -> str:
    if ref:
        return ref
    data = _github_api_get(f"/repos/{owner}/{repo}", token=token)
    default_branch = data.get("default_branch")
    if not default_branch:
        raise GithubFetchError("Không xác định được nhánh mặc định của repository.")
    return default_branch


def _safe_extract(tar_stream, dest_dir: str) -> str:
    dest_real = os.path.realpath(dest_dir)
    total_size = 0
    file_count = 0
    top_level_dirs = set()

    with tarfile.open(fileobj=tar_stream, mode="r|gz") as tar:
        for member in tar:
            file_count += 1
            if file_count > MAX_FILES:
                raise GithubFetchError("Repository có quá nhiều file, vượt giới hạn cho phép.")

            member_path = os.path.realpath(os.path.join(dest_dir, member.name))
            if member_path != dest_real and not member_path.startswith(dest_real + os.sep):
                continue  # path traversal attempt ("../"), silently skip
            if member.issym() or member.islnk():
                continue  # never follow symlinks/hardlinks from an untrusted archive

            top_level_dirs.add(member.name.split("/", 1)[0])

            if member.isdir():
                continue

            total_size += member.size
            if total_size > MAX_DOWNLOAD_BYTES:
                raise GithubFetchError("Repository vượt quá dung lượng cho phép (100MB).")

            tar.extract(member, path=dest_dir)

    if len(top_level_dirs) != 1:
        raise GithubFetchError("Định dạng tarball từ GitHub không như mong đợi.")
    return os.path.join(dest_dir, next(iter(top_level_dirs)))


def download_repo_snapshot(owner: str, repo: str, ref: str, dest_dir: str, token: str = None) -> str:
    """Download+extract a repo snapshot into dest_dir, returning the project root path."""
    safe_ref = quote(ref, safe="/")
    url = f"https://codeload.github.com/{quote(owner)}/{quote(repo)}/tar.gz/{safe_ref}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            os.makedirs(dest_dir, exist_ok=True)
            return _safe_extract(response, dest_dir)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GithubFetchError(
                f"Không tìm thấy nhánh '{ref}' hoặc repository trên GitHub."
            ) from exc
        raise GithubFetchError(f"Lỗi khi tải repository từ GitHub (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise GithubFetchError(f"Lỗi kết nối tới GitHub: {exc.reason}") from exc
    except tarfile.TarError as exc:
        raise GithubFetchError("Tarball tải về từ GitHub bị lỗi hoặc không đọc được.") from exc


def fetch_github_repo(url: str, dest_dir: str, token: str = None) -> str:
    """Parse a GitHub URL and download the repo snapshot into dest_dir.

    Returns the path to the extracted project root.
    """
    owner, repo, ref = parse_github_url(url)
    resolved_ref = resolve_ref(owner, repo, ref, token=token)
    return download_repo_snapshot(owner, repo, resolved_ref, dest_dir, token=token)
