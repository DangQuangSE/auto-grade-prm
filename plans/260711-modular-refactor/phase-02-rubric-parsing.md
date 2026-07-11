# Phase 2: Rubric Parsing Module Extraction

## Requirements

Extract rubric-parsing logic, constants, and helper functions from grader.py into a new root-level module rubric.py. This includes the HEURISTIC_MAPPING and DEFAULT_CRITERIA_TEXT constants, plus all parsing functions (_map_heuristic_key, _extract_weight, _clean_criterion_name, _looks_like_code_or_noise, _looks_like_criterion_name, _parse_weight_triplets, parse_rubric). Grader.py re-imports from rubric.py so all external callers of grader functions remain unaffected. Zero behavior change.

## Design Constraints

No behavior change — pure code movement of rubric-parsing logic. Functions are copied verbatim with no rewrites. Grader.py re-imports from rubric.py so that external code like `from grader import parse_rubric` and `from grader import DEFAULT_CRITERIA_TEXT` still works. The new rubric.py module has no dependencies on grader.py (no circular imports). Tests remain unmodified.

Preflight: This phase touches only grader.py and creates rubric.py (new). No app.py, templates, or test files are modified.

## Steps

1. Create rubric.py at the repo root (same level as grader.py, env_loader.py, etc.) and copy the following from grader.py into it: HEURISTIC_MAPPING (lines 9–25), DEFAULT_CRITERIA_TEXT (lines 27–41), and all parsing functions (_map_heuristic_key through parse_rubric, lines 44–177). Preserve all imports these functions need (json, os, re, Optional, Dict, Any from typing).

2. In grader.py, remove the copied code (lines 9–177) and add `from rubric import HEURISTIC_MAPPING, DEFAULT_CRITERIA_TEXT, parse_rubric` at the top, after the existing imports from providers.

3. Verify grader.py still imports parse_rubric and uses it in grade_project (line 446) and fallback_heuristic_grade (line 317); confirm DEFAULT_CRITERIA_TEXT is used in grade_project and fallback_heuristic_grade; confirm DEFAULT_RUBRIC at line 469 works (it should, since parse_rubric is now re-imported).

4. Run the Python test suite: `python -m unittest tests.test_grader tests.test_providers tests.test_document_parser tests.test_env_loader`. All should pass.

5. Run a smoke test: start the app, submit a grading request with default criteria (no custom criteria provided), confirm the rubric is parsed correctly and the report renders.

## Success Criteria

- rubric.py exists at repo root, contains HEURISTIC_MAPPING, DEFAULT_CRITERIA_TEXT, and all seven rubric-parsing functions.
- grader.py is reduced by ~170 lines and imports parse_rubric and DEFAULT_CRITERIA_TEXT from rubric.
- grader.py re-exports parse_rubric and DEFAULT_CRITERIA_TEXT so external callers see no change.
- No import errors when grader.py is imported.
- Python test suite passes (all four test modules).
- App loads, grading workflow completes with default criteria, report renders correctly.

## Quality and Testing State

- Quality gate: APPROVED (0 findings) — report at plans/260711-modular-refactor/quality/phase-02-rubric-parsing-quality-report.json, receipt at plans/260711-modular-refactor/quality/phase-02-rubric-parsing-receipt.json
- Testing: Python test suite passed (15/15). Browser smoke test (default-criteria grading run) not yet manually verified.

## Risks

- Incomplete extraction of helper functions: if _map_heuristic_key or _parse_weight_triplets are not copied to rubric.py but still called by parse_rubric, grader.py will error when parse_rubric is called. Mitigation: verify all functions used by parse_rubric (and the functions it calls) are copied into rubric.py; check imports and function call chains.
- Circular import: if rubric.py accidentally imports from grader.py, a circular dependency will fail. Mitigation: rubric.py should only import from standard library (re, json, os) and typing; no imports from grader, app, or providers.
- Missing re-export: if grader.py does not re-import parse_rubric and DEFAULT_CRITERIA_TEXT, external test code that does `from grader import parse_rubric` will fail. Mitigation: explicitly import these in grader.py's import section and verify tests still pass.
