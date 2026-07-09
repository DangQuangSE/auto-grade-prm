# Plan: OpenRouter Provider and User Criteria Templates

**Spec:** `plans/openrouter-criteria-provider/spec.md`  
**Mode:** Hard  
**Test mode:** default; recommend `--tdd` for implementation

---

## Scope Challenge

- **Exists?** Partially. The app already supports static Flutter analysis, custom criteria text, and Gemini-based AI grading, but the public API/UI and grader implementation are Gemini-specific.
- **Minimum?** Add OpenRouter env configuration, route grading through a provider-neutral function, accept dynamic criteria text/file content from UI, validate provider JSON, and keep heuristic fallback.
- **Complexity?** Hard. This is multi-file, touches API contract, frontend behavior, provider integration, credential handling, and response validation.

---

## Spec Quality Check

- **[NEEDS CLARIFICATION] remaining?** PASS. None remain in `spec.md`.
- **Success criteria measurable?** PASS. Criteria can be checked by API responses, provider config, UI/API naming, fallback behavior, and malformed JSON handling.
- **User stories P1/P2/P3?** PASS.
- **Acceptance criteria testable?** PASS, with one note: real OpenRouter success requires a valid `OPENROUTER_API_KEY` in the execution environment.

**Verdict:** PASS.

---

## Research Summary

### Primary Approach: Provider Module + Thin Orchestrator

Create a provider-neutral grading service in `grader.py`, move OpenRouter-specific HTTP logic into a small provider module, and keep analyzer output as evidence in the prompt.

**Verdict:** Recommended. It satisfies the spec with the smallest durable architecture.

### Alternative Approach: Inline OpenRouter Call in `grader.py`

Replace Gemini code directly with OpenRouter code inside the existing `grade_project_with_gemini` function.

**Verdict:** Faster initially, but keeps provider concerns tangled with rubric parsing, prompt building, fallback logic, and validation.

---

## Phases

- [x] **Phase 01 - Provider Foundation**
   - Files: `providers.py`, `grader.py`, optional `requirements.txt`
   - Covers: P1 OpenRouter provider, FR-01, FR-02, FR-06, FR-07

- [x] **Phase 02 - Grading Orchestration**
   - Files: `grader.py`, `app.py`
   - Covers: P1 dynamic criteria, P1 analyzer evidence, provider metadata, FR-03, FR-04, FR-05, FR-08, FR-10

- [x] **Phase 03 - Frontend Criteria Input**
   - Files: `templates/index.html`, `static/main.js`, `static/style.css`
   - Covers: P2 criteria upload, provider/model display, FR-09, privacy notice

- [x] **Phase 04 - Verification and Cleanup**
   - Files: tests if added, docs/env sample if added, touched source files
   - Covers: all success criteria and regression checks

---

## Risks

- OpenRouter's free model may not always obey strict JSON; implementation must validate and handle malformed responses.
- The existing repo has mojibake text in Vietnamese UI/source strings. Avoid broad text rewrites while touching only provider-related labels.
- No dependency manifest exists. Adding `requirements.txt` may be necessary to make HTTP client requirements explicit.
- End-to-end provider testing needs a real `OPENROUTER_API_KEY`; local automated tests should mock provider responses.

---

## Implementation Notes

- Use standard-library `urllib.request` for the first OpenRouter client to avoid adding a dependency manifest to the current repo.
- Read env vars as `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, optional `OPENROUTER_BASE_URL`, optional app metadata headers.
- Keep request API backward-compatible temporarily by accepting both `criteria_text` and legacy `custom_criteria`; the frontend should send `criteria_text`.
- Validate provider response shape before returning to UI:
  - `overall_score`: number from `0.0` to `10.0`
  - `criteria_breakdown`: object where each value has numeric `score` and string `feedback`
  - `summary`: string
  - `warnings`: list
- If provider fails, return a heuristic report based on the default criteria template and include clear `provider_error`, `warnings`, and fallback metadata. Do not expose the API key.

---

## Handoff

Recommended next command:

```text
/ck:cook --hard --tdd plans/openrouter-criteria-provider/plan.md
```

## Session Notes
<!-- Updated by cook automatically - do not edit manually -->

**Last active:** 2026-07-09 23:59
**Phase in progress:** none
**Status:** All phases implemented; runtime test execution is blocked by missing Python installation in this environment.

### Decisions made this session
- Used Python standard-library `urllib.request` for OpenRouter calls to avoid adding dependencies.
- Provider failures return `ProviderResult(ok=False, ...)` with sanitized error text.
- Provider response validation is centralized in `validate_grading_report`.
- Kept legacy `custom_criteria` request compatibility while making `criteria_text` the frontend field.
- Provider failures fall back to the default criteria template and include `provider_error`.
- Replaced the frontend API-key input with server-side provider status and criteria file upload.

### Next immediate action
Run the test suite on a machine with Python installed, then test a real OpenRouter grading request with `.env` configured.
