# Phase 03: Frontend Criteria Input

**Goal:** Update the UI so users provide criteria text or upload a criteria file, while OpenRouter credentials stay server-side.

**Stories Covered:** P2 criteria upload, provider/model visibility  
**Functional Requirements:** FR-09, FR-10

---

## Tasks

1. Remove Gemini API key input from `templates/index.html`.
2. Add a criteria file input that accepts `.md` and `.txt`.
3. Keep the criteria textarea as the primary editable source.
4. When a file is selected, read it in the browser and place its text in the textarea.
5. Update request payload in `static/main.js`:
   - send `criteria_text`
   - stop sending `gemini_key`
6. Add provider/model display if backend exposes config through an endpoint such as `/api/provider`.
7. Update loading and report labels to refer to OpenRouter/AI provider rather than Gemini.
8. Keep layout stable and avoid broad visual redesign.

---

## Tests to Write First

1. Empty criteria disables submit or shows a clear validation message.
2. Selecting a `.md` file populates the criteria textarea.
3. Submit payload contains `github_url` and `criteria_text`, not `gemini_key`.
4. Report rendering still supports dynamic `criteria_breakdown` keys.

---

## Acceptance Checks

- API key is not requested in the browser.
- Users can paste or upload criteria.
- Existing export/print report flow still works.
