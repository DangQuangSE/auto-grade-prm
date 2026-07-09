# Phase 01: Provider Foundation

**Goal:** Add a provider-neutral foundation with OpenRouter as the first concrete AI provider.

**Stories Covered:** P1 OpenRouter provider  
**Functional Requirements:** FR-01, FR-02, FR-06, FR-07

---

## Tasks

1. Create a provider module, likely `providers.py`.
2. Define a small provider result contract used by the grader:
   - success JSON payload
   - provider name
   - model id
   - error details for controlled fallback
3. Implement `OpenRouterProvider`.
4. Read configuration from environment:
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`, defaulting to `tencent/hy3:free` if absent
   - optional `OPENROUTER_BASE_URL`, defaulting to OpenRouter chat completions endpoint
5. Send chat completion requests with JSON-only instructions.
6. Validate and parse provider response JSON.
7. Add a retry or correction path for malformed JSON if practical.
8. Use Python standard-library HTTP calls first; do not add a new dependency unless implementation proves it is necessary.

---

## Tests to Write First

1. Provider config resolves `OPENROUTER_MODEL=tencent/hy3:free` from env.
2. Missing `OPENROUTER_API_KEY` returns a controlled unavailable result rather than raising an uncaught exception.
3. Valid mocked OpenRouter JSON is parsed into the expected report structure.
4. Malformed mocked OpenRouter output is rejected and surfaced as a controlled provider error.
5. Provider HTTP failures are surfaced as controlled provider errors without leaking credentials.

---

## Acceptance Checks

- No API key is printed or returned.
- Provider code is isolated from FastAPI route handling.
- The provider can be mocked without making a network call.
