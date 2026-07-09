# Brainstorm: OpenRouter AI provider and user-defined criteria templates

**Date:** 2026-07-09

## Ideas Explored

- Keep current heuristic grader only: simple, but criteria remains partly hard-coded through keyword mapping and cannot grade arbitrary rubrics well.
- Replace grading with AI-only: supports flexible criteria templates, but loses deterministic evidence from the existing static analyzer.
- Use a provider abstraction: lets the app call OpenRouter first and add other AI providers later without rewriting the grading flow.
- Add a criteria template input layer: users can paste or upload markdown/plain-text criteria per grading request instead of relying on `criteria.md`.
- Hybrid analyzer plus AI grading: preserve existing Flutter static analysis as evidence, then ask the AI provider to score against the user-provided template.

## User's Direction

The user wants grading criteria to be uploadable or entered by the user at grading time, not fixed in the codebase. The first AI integration should use the user's OpenRouter model.

## Open Questions

- Resolved: the default OpenRouter model should be read from `OPENROUTER_MODEL`, initially set to `tencent/hy3:free`.
- Resolved: the OpenRouter API key should be read from environment variables, not entered per request.
- Resolved: the MVP does not need a strict criteria template size limit.

## Risks

- AI output may be malformed unless the prompt enforces strict JSON and the backend validates the response before returning it.
- Arbitrary criteria templates may have missing weights, inconsistent totals, or vague requirements, so the app needs normalization and warnings.
- Sending source code to an external provider can expose sensitive code, so the UI/API should make the provider and transmitted context explicit.
