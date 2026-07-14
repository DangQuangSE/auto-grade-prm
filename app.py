import logging
import os
import tempfile
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from analyzer import analyze_flutter_project, validate_flutter_project
from document_parser import DocumentParseError, decode_text_content, extract_docx_text
from env_loader import load_dotenv
from github_fetch import GithubFetchError, fetch_github_repo
from grader import grade_project
from providers import get_provider_config
from repo_utils import clean_temp_dir, validate_git_url

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

ALLOW_LOCAL_PROJECT_PATH = os.getenv("ALLOW_LOCAL_PROJECT_PATH", "false").strip().lower() == "true"

app = FastAPI(title="Flutter Code Auto-Grader")

# Define request models
class GradeRequest(BaseModel):
    github_url: str
    criteria_text: Optional[str] = None
    custom_criteria: Optional[str] = None

class CriteriaExtractRequest(BaseModel):
    filename: str
    content_base64: str

# Repos are downloaded into the OS temp dir (resolves to /tmp on Vercel,
# the only writable path in that read-only serverless filesystem).
TEMP_DIR = os.path.join(tempfile.gettempdir(), "flutter_autograder_repos")
os.makedirs(TEMP_DIR, exist_ok=True)

# Mount static files
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = os.path.join(templates_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h3>Frontend index.html is still being generated. Please wait...</h3>"

@app.get("/api/criteria")
async def get_criteria():
    criteria_file = os.path.join(BASE_DIR, "criteria.md")
    if os.path.exists(criteria_file):
        with open(criteria_file, 'r', encoding='utf-8') as f:
            return {"criteria": f.read()}
    return {"criteria": "Không tìm thấy tiêu chí cụ thể. Vui lòng tự cung cấp."}

@app.get("/api/provider")
async def get_provider():
    return get_provider_config()

@app.post("/api/criteria/extract")
async def extract_criteria(request: CriteriaExtractRequest):
    filename = request.filename.lower().strip()
    try:
        if filename.endswith(".docx"):
            text = extract_docx_text(request.content_base64)
        elif filename.endswith(".md") or filename.endswith(".txt"):
            text = decode_text_content(request.content_base64)
        else:
            raise DocumentParseError("Only .docx, .md, and .txt criteria files are supported.")
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"criteria": text}

@app.post("/api/grade")
async def grade_repository(request: GradeRequest, background_tasks: BackgroundTasks):
    github_url = request.github_url.strip()

    # Check if URL is local path or git repo (only if explicitly enabled)
    is_local = ALLOW_LOCAL_PROJECT_PATH and os.path.exists(github_url) and os.path.isdir(github_url)
    
    if not is_local:
        if not (github_url.startswith("http://") or github_url.startswith("https://") or github_url.startswith("git@")):
            invalid_path_detail = (
                "Đường dẫn không hợp lệ. Vui lòng nhập link GitHub hoặc đường dẫn thư mục cục bộ."
                if ALLOW_LOCAL_PROJECT_PATH
                else "Đường dẫn không hợp lệ. Vui lòng nhập link GitHub hợp lệ (ví dụ: https://github.com/owner/repo)."
            )
            raise HTTPException(status_code=400, detail=invalid_path_detail)

        # Validate git host against allowlist (SSRF protection)
        validate_git_url(github_url)

        # Download repository snapshot via GitHub's HTTP API (no git binary,
        # no writable repo-relative filesystem required — safe for serverless).
        repo_id = str(uuid.uuid4())
        clone_dir = os.path.join(TEMP_DIR, repo_id)

        try:
            target_path = fetch_github_repo(github_url, clone_dir, token=os.getenv("GITHUB_TOKEN"))
        except GithubFetchError as exc:
            clean_temp_dir(clone_dir)
            logger.warning(f"Fetch failed for {github_url}: {exc}")
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            clean_temp_dir(clone_dir)
            logger.exception(f"Fetch failed for {github_url}")
            raise HTTPException(status_code=500, detail="Lỗi khi tải repository. Vui lòng kiểm tra lại đường dẫn hoặc thử lại sau.")
    else:
        target_path = github_url
        
    try:
        validation_error = validate_flutter_project(target_path)
        if validation_error:
            raise HTTPException(status_code=400, detail=validation_error)

        # 1. Run static analysis
        analysis_report = analyze_flutter_project(target_path)
        if "error" in analysis_report:
            raise Exception(analysis_report["error"])

        criteria_text = request.criteria_text or request.custom_criteria

        # 2. Run AI provider grading or fallback heuristic
        result_report = grade_project(
            target_path,
            analysis_report,
            criteria_text
        )

        # Add metadata
        result_report["repository"] = github_url
        result_report["is_local"] = is_local

        # If it was downloaded, schedule cleanup in background tasks
        if not is_local:
            background_tasks.add_task(clean_temp_dir, clone_dir)

        return result_report

    except HTTPException:
        if not is_local:
            clean_temp_dir(clone_dir)
        raise
    except Exception as e:
        if not is_local:
            clean_temp_dir(clone_dir)
        logger.exception(f"Error grading project at {target_path}")
        raise HTTPException(status_code=500, detail="Lỗi khi phân tích và chấm điểm dự án. Vui lòng thử lại sau.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
