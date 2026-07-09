# Spec: OpenRouter Provider and User Criteria Templates

**Date:** 2026-07-09
**Status:** Draft

---

## Problem Statement

The current Flutter auto-grader is tied to a Gemini-specific implementation and a mostly fixed rubric. Users need to grade Flutter projects against criteria they paste or upload, using an OpenRouter-backed AI model while still benefiting from the existing static analyzer.

---

## User Stories

- **[P1]** As an instructor, I want to paste a criteria template when grading a repository so that each assignment can use its own rubric.
  Accepted when: a grading request with custom criteria produces a JSON report whose `criteria_breakdown` follows the submitted criteria names.

- **[P1]** As an instructor, I want to use my OpenRouter API key and model so that grading is powered by my chosen AI provider.
  Accepted when: the backend can call OpenRouter using `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` from the server environment.

- **[P1]** As a user, I want the grader to combine static Flutter analysis with AI judgment so that scores are grounded in observed project evidence.
  Accepted when: the AI prompt includes the analyzer report and selected source excerpts, and the returned report references criteria-specific evidence.

- **[P2]** As an instructor, I want to upload a `.md` or `.txt` criteria template so that I do not need to paste long rubrics manually.
  Accepted when: the UI accepts a text criteria file and sends its content to the grading API.

- **[P2]** As a user, I want clear validation messages for invalid criteria so that I can fix missing weights or unreadable templates before grading.
  Accepted when: requests with empty or unreadable criteria return actionable validation errors.

- **[P3]** _(out of scope - noted for future)_ Manage saved criteria templates with names, versions, and reuse history.

---

## Functional Requirements

1. FR-01: Replace Gemini-specific request fields with provider-neutral fields: `provider` and `criteria_text`; OpenRouter credentials and model are read from environment variables.
2. FR-02: Add an OpenRouter provider implementation that calls the OpenRouter chat completions API using `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`.
3. FR-03: Preserve the current static analyzer and pass its JSON report into the AI grading prompt as evidence.
4. FR-04: Allow users to enter criteria as free-form text, markdown table, or weighted list.
5. FR-05: Parse criteria names and weights when possible; if weights are missing, normalize criteria evenly and include a warning.
6. FR-06: Require the AI response to be valid JSON with `overall_score`, `criteria_breakdown`, `summary`, and `warnings`.
7. FR-07: Validate the AI response before returning it; if invalid, retry once with a correction prompt or return a controlled error.
8. FR-08: Keep a non-AI fallback path for cases where no API key is provided, but label it clearly as heuristic grading.
9. FR-09: Update the frontend to accept criteria text and optional criteria file upload, while showing the configured OpenRouter provider/model when available.
10. FR-10: Remove hard-coded Gemini naming from user-facing labels, API field names, and summaries.

---

## Non-Functional Requirements

- Performance: Complete static analysis plus AI grading in under 120 seconds for a Flutter project with up to 200 Dart files.
- Security: Do not log API keys; OpenRouter credentials must be read from environment variables such as `OPENROUTER_API_KEY`.
- Privacy: Show that code excerpts and analyzer output are sent to the selected AI provider before grading starts.
- Reliability: Return structured backend errors for clone failures, criteria validation failures, provider failures, and malformed AI responses.
- Maintainability: Adding another provider should require a new provider class/function and no changes to the main grading route.

---

## Success Criteria

- [ ] Dynamic criteria: 3 different criteria templates produce reports with matching `criteria_breakdown` keys.
- [ ] OpenRouter call: valid `OPENROUTER_API_KEY` and `OPENROUTER_MODEL=tencent/hy3:free` return a successful grading report.
- [ ] Provider isolation: no Gemini-specific names remain in the public API or UI for the main grading path.
- [ ] Fallback behavior: grading without an API key still returns a heuristic report with a clear fallback summary.
- [ ] JSON validation: malformed provider output is caught and does not crash the API.

---

## Out of Scope

- User accounts, billing, or storing API keys.
- Persisted template library or template versioning.
- Full semantic parsing of all Dart files.
- Fine-tuning or training a custom model.

---

## Assumptions

- The first provider target is OpenRouter.
- The default model is `tencent/hy3:free`, configured through `OPENROUTER_MODEL`.
- The OpenRouter API key is configured through environment variable `OPENROUTER_API_KEY`.
- The backend remains a FastAPI application.
- The existing analyzer output is useful as grounding evidence and should be kept.
- Criteria templates are text-based in the first version.
- Criteria templates do not need a strict maximum size in the MVP.
- Scores remain on a 0.0 to 10.0 scale.
