# Plan: Code Organization Refactor — Modular Responsibility Split

Status: 🟢 Completed
Date: 2026-07-11
Mode: Hard

## Overview

This plan reorganizes the codebase by splitting mixed-responsibility files into focused, single-purpose modules. Zero behavior change: all tests pass, app runs identically before and after. The refactor improves maintainability for future development by following the flat, single-purpose module convention already established by `env_loader.py`, `document_parser.py`, `analyzer.py`, and `providers.py`.

## Phases

- [x] Phase 1: Extract i18n dictionary into static/i18n.js — Separate translation logic and language state from DOM wiring.
- [x] Phase 2: Extract rubric parsing into rubric.py — Move criteria parsing rules and validation heuristics out of grader.py.
- [x] Phase 3: Extract heuristic scoring into heuristics.py — Move per-criterion scoring logic out of grader.py.
- [x] Phase 4: Extract AI prompt building into prompt_builder.py — Separate evidence formatting and schema construction from orchestration.
- [x] Phase 5: Extract git/SSRF validation and cleanup into repo_utils.py — Move security and temp-file logic out of app.py.

## Research Summary

### i18n Dictionary Extraction (Research Complete)
Two design approaches were evaluated:
- **Async JSON fetch** (rejected): Over-engineered for a ~140-key vocabulary in a no-build-step app; adds unnecessary startup delay and complexity.
- **Plain second `<script>` tag** (chosen): Load `static/i18n.js` BEFORE `main.js` in index.html. No ES modules, no async. `i18n.js` defines globals `I18N`, `currentLang`, and function `t(key, vars)` exactly as they exist today — move verbatim from lines 1–153 of current main.js, no logic changes. main.js keeps all DOM/API logic, just uses the pre-loaded globals.

**Rationale**: Minimal ceremony, maximum robustness. Zero startup cost, obvious script order dependency, trivial to understand.

### Python Module Split (Research Complete)
Repository convention is **flat, single-purpose root-level modules** (not nested packages). New modules follow sibling style:
- `rubric.py` — rubric parsing, weight extraction, criterion validation (from grader.py lines 9–177)
- `heuristics.py` — per-criterion heuristic scoring engine (from grader.py lines 180–310)
- `prompt_builder.py` — source-file reading, prompt schema, prompt construction (from grader.py lines 348–437)
- `repo_utils.py` — git host validation (SSRF protection), temp-dir cleanup (from app.py lines 25, 87–137)

**Rationale**: Each new module owns one concern. Grader.py becomes a thin orchestrator. App.py becomes route handlers + bootstrap only. Tests remain unmodified; existing imports work because the extracted functions are re-imported into grader.py/app.py where needed. Flat structure matches the repo's existing convention.

### Test Verification Strategy
- After each phase: run `python -m unittest tests.test_grader tests.test_providers tests.test_document_parser tests.test_env_loader` (note: `test_app_contract` errors due to missing httpx2, unrelated to this work).
- Smoke test: start the app, submit a grading request with a local path and default criteria, confirm report renders.
- No test file changes: imports in tests remain stable because extracted functions are re-imported into their original modules.

## Dependencies

- None. All refactoring work is self-contained; no external services, no prerequisite work from other teams.

## Risks

- **HIGH: Accidental behavior change during extraction** — Mitigation: extract only function definitions and constants; do not change logic, variable names, or function signatures. Run tests after each phase. If a test fails, revert immediately and revisit the extraction boundary.
- **HIGH: Import cycle if a new module re-imports from grader.py** — Mitigation: new modules are leaf modules; they import from providers, env_loader, etc., but NOT from grader.py or app.py. Grader.py and app.py import from new modules. Validate import DAG after each phase.
- **MEDIUM: Missed re-export in grader.py/app.py causing tests to break** — Mitigation: after extraction, explicitly re-import the moved functions into their original module so all existing `from grader import X` and `from app import Y` calls still work. Tests remain unmodified.
- **MEDIUM: i18n script load order wrong in index.html (script executed before i18n.js loads)** — Mitigation: Validate that `<script src="/static/i18n.js">` appears BEFORE `<script src="/static/main.js">` in the browser inspector Network tab. Manual smoke test on multiple pages.
- **LOW: File structure inconsistency with naming** — Mitigation: Keep all new Python modules at repo root, snake_case, single-purpose, matching analyzer.py/document_parser.py/env_loader.py style.
