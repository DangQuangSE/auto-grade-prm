# Phase 4: AI Prompt Building Module Extraction

## Requirements

Extract the AI prompt-building logic from grader.py into a new root-level module prompt_builder.py. This includes get_key_files_content (lines 348–382) and build_grading_prompt (lines 385–437 in current grader.py). Grader.py re-imports from prompt_builder.py so all external callers remain unaffected. Zero behavior change.

## Design Constraints

No behavior change — pure code movement of prompt-building logic. Functions are copied verbatim with no rewrites or logic changes. Grader.py re-imports from prompt_builder.py so that external code using these functions continues to work. The new prompt_builder.py module imports from rubric.py but not from grader.py or heuristics.py (no circular imports). Tests remain unmodified.

Preflight: This phase touches only grader.py and creates prompt_builder.py (new). Phases 2 and 3 must be completed first; this phase does not depend on heuristics.py but relies on rubric.py being available.

## Steps

1. Create prompt_builder.py at the repo root and copy the following from grader.py: get_key_files_content (lines 348–382) and build_grading_prompt (lines 385–437). Preserve all imports these functions need (json, os, Dict, Any from typing).

2. At the top of prompt_builder.py, ensure all imports are present; no imports from grader.py, heuristics.py, or app.py.

3. In grader.py, remove lines 348–437 (get_key_files_content and build_grading_prompt) and add `from prompt_builder import get_key_files_content, build_grading_prompt` at the top, after existing imports.

4. Verify grader.py still uses these functions in grade_project (lines 391 and 447 in original numbering, will shift due to phases 2–3). Re-export both functions at the grader.py module level so external callers see no change.

5. Run the Python test suite: `python -m unittest tests.test_grader tests.test_providers tests.test_document_parser tests.test_env_loader`. All should pass.

6. Run a smoke test: start the app, submit a grading request with custom criteria, confirm the prompt is built correctly (check app logs or add temporary debug output), and confirm the report renders successfully.

## Success Criteria

- prompt_builder.py exists at repo root, contains get_key_files_content and build_grading_prompt.
- prompt_builder.py imports only standard library modules and typing; no imports from grader.py, heuristics.py, or app.py.
- grader.py is reduced by ~90 lines and imports both functions from prompt_builder.py.
- grader.py re-exports both functions so external callers see no change.
- No import errors when grader.py is imported.
- Python test suite passes (all four test modules).
- App loads, grading workflow completes with custom criteria, prompt is built and sent to AI provider or fallback, report renders.

## Quality and Testing State

- Quality gate: APPROVED (0 findings) — report at plans/260711-modular-refactor/quality/phase-04-prompt-building-quality-report.json, receipt at plans/260711-modular-refactor/quality/phase-04-prompt-building-receipt.json
- Testing: Python test suite passed (15/15). Browser smoke test (custom-criteria grading run) not yet manually verified.

## Risks

- Incomplete extraction: if build_grading_prompt calls a helper function not copied, it will error. Mitigation: verify both functions are self-contained and have all necessary imports; trace through function calls.
- Logic error in prompt construction: if the prompt schema or evidence formatting is accidentally changed during extraction, grading results may differ. Mitigation: after extraction, compare the prompt output (before sending to AI provider) against the original by adding debug output or logging; ensure identical.
- Re-export forgotten: if grader.py does not re-import get_key_files_content and build_grading_prompt, external code may fail (though none exists in tests currently). Mitigation: explicitly add both imports to grader.py.
