# Phase 5: Repository Utilities Module Extraction

## Requirements

Extract git-validation and temp-directory-cleanup logic from app.py into a new root-level module repo_utils.py. This includes the ALLOWED_GIT_HOSTS constant (line 25), clean_temp_dir function (lines 87–91), and validate_git_url function (lines 93–137). App.py re-imports from repo_utils.py so all route handlers and middleware remain unaffected. Zero behavior change.

## Design Constraints

No behavior change — pure code movement of SSRF-protection and cleanup logic. Functions and constants are copied verbatim with no rewrites or logic changes. App.py re-imports from repo_utils.py so that internal uses of these functions (like validate_git_url in grade_repository and clean_temp_dir in grade_repository) continue to work. The new repo_utils.py module imports only standard library (logging, os, shutil, subprocess, urllib.parse from urllib); no imports from app.py, grader.py, or other custom modules (no circular imports). Tests remain unmodified.

Preflight: This phase touches only app.py and creates repo_utils.py (new). All previous phases (1–4) must be completed first. This phase does not depend on grader.py extraction phases but is isolated to app.py.

## Steps

1. Create repo_utils.py at the repo root and copy the following from app.py: ALLOWED_GIT_HOSTS constant (line 25), clean_temp_dir function (lines 87–91), and validate_git_url function (lines 93–137). Preserve all imports these need (logging, os, shutil, subprocess, urllib.parse from urllib; typing.Optional).

2. At the top of repo_utils.py, set up a logger: `logger = logging.getLogger(__name__)`. This is optional but recommended for consistency with app.py's logging pattern.

3. In app.py, remove lines 25, 87–91, and 93–137, and add `from repo_utils import ALLOWED_GIT_HOSTS, clean_temp_dir, validate_git_url` at the top, after existing imports.

4. Verify app.py still uses these in grade_repository (lines 144–199 in original, will shift): validate_git_url is called at line 156, clean_temp_dir is called at lines 172, 199, and 205. Re-export (or ensure they are accessible) so internal uses in app.py routes work.

5. Run the Python test suite: `python -m unittest tests.test_grader tests.test_providers tests.test_document_parser tests.test_env_loader`. All should pass. (Note: test_app_contract may error due to missing httpx2, which is pre-existing and not a regression from this work.)

6. Run a smoke test: start the app, submit a grading request with a valid GitHub URL (e.g., a public test repo), confirm the repository is cloned and graded, and the temp directory is cleaned up afterward (verify /temp_repos is empty after grading completes).

## Success Criteria

- repo_utils.py exists at repo root, contains ALLOWED_GIT_HOSTS, clean_temp_dir, and validate_git_url.
- repo_utils.py imports only standard library modules and typing; no imports from app.py, grader.py, or custom modules.
- app.py is reduced by ~50 lines and imports all three from repo_utils.py.
- app.py grade_repository route still uses validate_git_url and clean_temp_dir; no import errors.
- No import errors when app.py is imported.
- Python test suite passes (all four test modules; test_app_contract pre-existing error is acceptable).
- App loads, grading with valid Git URL works (clone, analyze, grade, temp cleanup), security validation rejects invalid hosts.

## Quality and Testing State

- Quality gate: APPROVED (0 findings, SSRF logic verified byte-exact) — report at plans/260711-modular-refactor/quality/phase-05-repo-utilities-quality-report.json, receipt at plans/260711-modular-refactor/quality/phase-05-repo-utilities-receipt.json
- Testing: Python test suite passed (15/15). Browser smoke test (valid Git URL clone + temp cleanup) not yet manually verified.

## Risks

- SSRF validation logic broken: if validate_git_url is not copied exactly, the allowlist check may fail or become permissive. Mitigation: compare validate_git_url in repo_utils.py byte-by-byte with the original in app.py; trace through hostname extraction logic for both http(s) and git@ URL formats.
- Logger not initialized: if repo_utils.py uses logger but does not initialize it, logging will fail silently. Mitigation: add `logger = logging.getLogger(__name__)` at the top of repo_utils.py.
- Re-import forgotten: if app.py does not re-import validate_git_url or clean_temp_dir, the grade_repository route will error. Mitigation: explicitly add the imports and verify the app starts and a test grading request works.
- Temp-dir not cleaned: if clean_temp_dir is not called at all, temp_repos will grow over time and tests may fail due to missing space. Mitigation: verify that grade_repository still calls clean_temp_dir in background_tasks and after error handling (line 199 in original).
