# Phase 04: Verification and Cleanup

**Goal:** Verify the full provider-backed grading flow and remove stale Gemini-facing behavior.

**Stories Covered:** All P1/P2 stories  
**Functional Requirements:** All FRs

---

## Tasks

1. Search for Gemini-specific public names and update or isolate them.
2. Add `.env.example` if appropriate:
   - `OPENROUTER_API_KEY=`
   - `OPENROUTER_MODEL=tencent/hy3:free`
3. Run unit tests for provider parsing, fallback, and criteria parsing.
4. Run FastAPI smoke checks:
   - `/api/criteria`
   - `/api/provider` if added
   - `/api/grade` mocked or local fallback path
5. Manually test UI flow:
   - paste criteria
   - upload `.md` or `.txt`
   - local project path or sample repo
   - export Markdown
6. Confirm sensitive values are not logged or returned.
7. Document any provider test that could not be run without a real API key.
8. Verify that provider failure still returns a fallback report and includes an explicit provider error.

---

## Tests to Write First

1. Regression test for malformed provider JSON.
2. Regression test for missing env API key falling back to default-template heuristic grading.
3. Regression test for dynamic criteria names in the final report.
4. Search-based verification that user-facing Gemini labels are removed.

---

## Acceptance Checks

- All success criteria in `spec.md` have an explicit verification result.
- No main UI/API path asks for Gemini credentials.
- The app degrades clearly when OpenRouter is not configured.
