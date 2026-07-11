# Phase 3: Heuristic Scoring Module Extraction

## Requirements

Extract the heuristic-scoring engine from grader.py into a new root-level module heuristics.py. This includes the get_heuristic_score_for_key function and the fallback_heuristic_grade function (lines 180–345 in current grader.py). Grader.py re-imports from heuristics.py so all external callers remain unaffected. Zero behavior change.

## Design Constraints

No behavior change — pure code movement of heuristic-scoring logic. Functions are copied verbatim with no rewrites or logic changes. Grader.py re-imports from heuristics.py so that external code like `from grader import fallback_heuristic_grade` still works. The new heuristics.py module imports from rubric.py (for DEFAULT_CRITERIA_TEXT and parse_rubric) but not from grader.py (no circular imports). Tests remain unmodified.

Preflight: This phase touches only grader.py and creates heuristics.py (new). Phase 2 (rubric.py extraction) must be completed first so heuristics.py can import from rubric.py.

## Steps

1. Create heuristics.py at the repo root and copy the following from grader.py: get_heuristic_score_for_key (lines 180–310) and fallback_heuristic_grade (lines 312–345). Preserve all imports these functions need (Dict, Any from typing).

2. At the top of heuristics.py, add `from rubric import DEFAULT_CRITERIA_TEXT, parse_rubric` so fallback_heuristic_grade can use parse_rubric and DEFAULT_CRITERIA_TEXT.

3. In grader.py, remove lines 180–345 and add `from heuristics import get_heuristic_score_for_key, fallback_heuristic_grade` at the top, after existing imports.

4. Verify grader.py still imports fallback_heuristic_grade and uses it in grade_project (line 459 in the original line numbering, will shift due to phase 2). Re-export both functions at the grader.py module level so external callers see no change.

5. Run the Python test suite: `python -m unittest tests.test_grader tests.test_providers tests.test_document_parser tests.test_env_loader`. All should pass.

6. Run a smoke test: start the app, submit a grading request where the AI provider will fail (simulate or use a bad API key), confirm the heuristic fallback activates and generates a score/report without errors.

## Success Criteria

- heuristics.py exists at repo root, contains get_heuristic_score_for_key and fallback_heuristic_grade.
- heuristics.py imports from rubric.py; no imports from grader.py or app.py.
- grader.py is reduced by ~165 lines and imports both functions from heuristics.py.
- grader.py re-exports both functions so external callers see no change.
- No import errors when grader.py is imported.
- Python test suite passes (all four test modules).
- App loads, fallback heuristic grading works correctly when AI provider is unavailable or misconfigured.

## Quality and Testing State

- Quality gate: APPROVED (0 findings) — report at plans/260711-modular-refactor/quality/phase-03-heuristic-scoring-quality-report.json, receipt at plans/260711-modular-refactor/quality/phase-03-heuristic-scoring-receipt.json
- Testing: Python test suite passed (15/15). Browser smoke test (AI-provider-failure fallback) not yet manually verified.

## Risks

- Missed function dependency: if fallback_heuristic_grade calls a function or constant not copied to heuristics.py, it will error. Mitigation: verify all internal references within fallback_heuristic_grade are satisfied; check that parse_rubric and DEFAULT_CRITERIA_TEXT are imported from rubric.py.
- Import chain broken: if heuristics.py is missing the rubric.py import, fallback_heuristic_grade will error when parse_rubric is called. Mitigation: explicitly import from rubric.py at the top of heuristics.py and test immediately.
- Re-export forgotten: if grader.py does not re-import fallback_heuristic_grade, code like `from grader import fallback_heuristic_grade` will fail. Mitigation: explicitly add the import in grader.py and verify tests pass.
