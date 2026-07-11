# Phase 1: i18n Dictionary Extraction

## Requirements

Move the i18n dictionary, language state, and translation function from main.js (lines 1–153) into a separate static/i18n.js file loaded as a global script before main.js. Both files will remain in the static/ folder; index.html will load both in order. This phase produces zero behavior change and no DOM/API logic moves.

## Design Constraints

No behavior change — pure code movement. The i18n dictionary and translation logic are moved verbatim to i18n.js with no rewrites. Main.js still uses the now-global `I18N`, `currentLang`, and `t()` function identically. Existing tests pass unmodified (they do not test frontend code). Script load order must guarantee i18n.js loads before main.js or main.js will fail.

Preflight: This phase touches only static/main.js, static/i18n.js (new), and templates/index.html. No Python code is affected.

## Steps

1. Create static/i18n.js and copy lines 1–153 from current main.js verbatim (the entire I18N object, currentLang variable, and t() function definition).

2. Delete lines 1–153 from main.js; verify main.js now starts with `document.addEventListener("DOMContentLoaded"...` (line 155 becomes line 1).

3. In templates/index.html, add `<script src="/static/i18n.js"></script>` BEFORE the existing `<script src="/static/main.js"></script>` tag to guarantee i18n globals are defined before main.js runs.

4. Start the app and manually verify: in browser inspector, check that i18n.js loads, then main.js loads in that order; switch language (VI/EN) and confirm text updates; submit a grading request with default criteria and confirm report renders with correct language.

5. Run the Python test suite to confirm no regressions: `python -m unittest tests.test_grader tests.test_providers tests.test_document_parser tests.test_env_loader`.

## Success Criteria

- static/i18n.js exists and contains the I18N dictionary, currentLang, and t() function, moved verbatim.
- main.js is reduced by ~150 lines and no longer contains i18n dictionary or currentLang; starts with DOMContentLoaded listener.
- index.html loads both scripts in order: i18n.js before main.js.
- Browser Network tab shows i18n.js loaded before main.js, no 404 errors.
- App loads, language switch works (VI ↔ EN), grading workflow completes and report renders with correct language.
- Python test suite passes (all four test modules).

## Quality and Testing State

- Quality gate: APPROVED (0 findings) — report at plans/260711-modular-refactor/quality/phase-01-i18n-extraction-quality-report.json, receipt at plans/260711-modular-refactor/quality/phase-01-i18n-extraction-receipt.json
- Testing: Python test suite passed (15/15). Browser smoke test (language switch, grading workflow) not yet manually verified.

## Risks

- Load-order failure: if index.html accidentally loads main.js before i18n.js, main.js will error when trying to use undefined i18n globals. Mitigation: verify script tag order in index.html and confirm in browser Network tab.
- Copy/paste error during extraction: if lines 1–153 are not copied exactly, functions like t() may be incomplete. Mitigation: after creation, diff main.js old lines 1–153 vs. i18n.js to verify byte-exact match; use a text editor diff tool.
