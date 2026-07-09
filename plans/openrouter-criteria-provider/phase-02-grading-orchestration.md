# Phase 02: Grading Orchestration

**Goal:** Refactor grading flow so dynamic criteria and analyzer evidence are passed to OpenRouter through a provider-neutral orchestration function.

**Stories Covered:** P1 dynamic criteria, P1 analyzer evidence  
**Functional Requirements:** FR-03, FR-04, FR-05, FR-08, FR-10

---

## Tasks

1. Rename or replace `grade_project_with_gemini` with provider-neutral naming, such as `grade_project`.
2. Keep `parse_rubric`, `fallback_heuristic_grade`, and `get_key_files_content`, but remove Gemini-specific language from comments and summaries.
3. Build a prompt that includes:
   - user criteria text
   - parsed criteria names and weights if available
   - static analyzer JSON
   - selected source excerpts
   - strict response schema
4. Update `app.py` request model:
   - keep `github_url`
   - replace `gemini_key` with no per-request key
   - use `criteria_text` as the new criteria field
   - accept legacy `custom_criteria` temporarily for backward compatibility
5. Validate criteria input:
   - reject empty or unreadable criteria text for AI grading requests
   - fallback to `criteria.md` only where current default behavior is intentionally preserved
6. Add provider/fallback metadata to responses:
   - `provider`
   - `model`
   - `grading_mode`: `ai` or `heuristic`
7. Add a small provider config endpoint, such as `/api/provider`, that returns safe public metadata:
   - provider name
   - configured model id
   - whether an API key is configured, as a boolean only
8. Ensure fallback behavior works when env key is missing or provider call fails:
   - fallback uses the default criteria template
   - response includes `provider_error`
   - response includes `grading_mode: "heuristic"`
   - response warnings mention that AI grading failed

---

## Tests to Write First

1. API route passes `criteria_text` into `grade_project`.
2. `custom_criteria` compatibility path still works if kept.
3. Fallback report labels itself as heuristic and does not mention Gemini.
4. Criteria without explicit weights produces normalized scoring instructions and a warning.
5. Provider failure returns a controlled heuristic fallback with `provider_error`.
6. `/api/provider` does not expose the API key and reports `tencent/hy3:free` when that is the configured model.

---

## Acceptance Checks

- Public backend names no longer expose Gemini in the main grading path.
- Existing local path and Git clone behavior remains unchanged.
- Analyzer report remains included in the AI prompt.
