import logging
import shutil
import urllib.parse

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Security configuration
# Repos are fetched via GitHub's HTTP API/codeload (no git binary, no writable
# repo-relative filesystem required), so only github.com is supported.
ALLOWED_GIT_HOSTS = {"github.com"}


def clean_temp_dir(path):
    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def validate_git_url(url: str) -> str:
    """
    Validate git URL against allowlist of hosts.
    Returns the hostname if valid, otherwise raises HTTPException.
    Handles both http(s) and git@ SCP-style URLs.
    """
    # Handle git@host:path/to/repo.git style URLs
    if url.startswith("git@"):
        # Extract host between git@ and : or /
        remainder = url[4:]
        end_idx = min(
            (remainder.find(":") if ":" in remainder else len(remainder)),
            (remainder.find("/") if "/" in remainder else len(remainder))
        )
        if end_idx == len(remainder) and ":" not in remainder and "/" not in remainder:
            end_idx = len(remainder)
        hostname = remainder[:end_idx]
    else:
        # Parse http(s) URLs
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname or ""

    if not hostname:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ link GitHub (ví dụ: https://github.com/owner/repo)."
        )

    hostname_lower = hostname.lower()

    # Check if hostname is in allowlist or is a subdomain of an allowed host
    is_allowed = hostname_lower in ALLOWED_GIT_HOSTS
    if not is_allowed:
        for allowed_host in ALLOWED_GIT_HOSTS:
            if hostname_lower.endswith("." + allowed_host):
                is_allowed = True
                break

    if not is_allowed:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ link GitHub (ví dụ: https://github.com/owner/repo)."
        )

    return hostname_lower
