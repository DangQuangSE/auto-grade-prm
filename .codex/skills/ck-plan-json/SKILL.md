---
name: ck:plan-json
description: Create a structured JSON plan from a spec or feature description. Outputs plan.json — parseable by AI for step-by-step autonomous execution + debugging. Use when you want a machine-readable plan that ck:cook can execute with exact step tracking.
user-invocable: true
---

# ck:plan-json — Structured JSON Planning

Generates `plans/{slug}/plan.json` with explicit steps, status tracking, file dependencies, and debug log slots — designed for AI-driven autonomous coding.

---

### Step 0 — Load Input

Resolve the primary requirement input in this order:
1. `--spec <path>` — load the spec.md at `{path}`. This is the preferred input.
2. If no spec: `{inline text}` — use the command-line description as requirement.
3. If neither: ask "Describe what you want to build, or provide a path to spec.md".

Also accept:
- `--project {slug}` — project id (default: CWD name)
- `--mode {fast|hard}` — fast for single-file, hard for multi-phase (default: auto-detect from scope)

---

### Step 1 — Scope Analysis

Analyze the requirement to determine:

```
Scope:
  Phases:   [N]
  Files:    [N total, N new, N modify]
  Complexity: [Fast | Hard]
```

- **Fast** — 1 phase, ≤3 files, single component, no external dependencies
- **Hard** — 2+ phases, 4+ files, multiple components, external integrations

If hard and no spec provided → suggest "/ck:brainstorm first? [Y/n]"

---

### Step 2 — Generate plan.json

Write `plans/{slug}/plan.json` with the following exact structure:

```json
{
  "plan_id": "{slug}",
  "goal": "{one-line description of what the plan delivers}",
  "current_step": 1,
  "global_context": {
    "framework": "{detected framework or empty}",
    "architecture": "{architectural pattern}",
    "target_folder": "{primary output directory}",
    "constraints": []
  },
  "steps": [
    {
      "step_id": 1,
      "phase": "{kebab-case-phase-name}",
      "description": "{actionable description of what to do in this step}",
      "status": "pending",
      "input_files": [],
      "output_files": ["{path/to/file/to/create}"],
      "ai_generated_code": "",
      "debug_logs": [],
      "success_criteria": ["{verifiable condition}"]
    }
  ]
}
```

**Rules:**
- `current_step`: always `1` at creation (ck:cook increments it)
- `status`: `"pending"` for all steps (ck:cook updates to in_progress/completed/failed)
- `input_files`: list of files that must exist BEFORE this step (from prior steps or existing codebase)
- `output_files`: files this step creates/modifies
- `ai_generated_code`: leave empty string — ck:cook fills this with generated code paths
- `debug_logs`: leave empty array — ck:cook appends debug entries on failure
- `success_criteria`: specific, verifiable conditions (not "should work" — "All unit tests pass")

**Phase naming convention:**
| Phase | When |
|---|---|
| `setup-project` | First phase — init, deps, config |
| `implement-{domain}` | Core feature logic |
| `implement-api` | API endpoints |
| `implement-ui` | Frontend components |
| `add-tests` | Test coverage |
| `integrate` | Wire components together |
| `document` | Docs, README |

---

### Step 3 — Validate plan.json

Read back the written file and validate:

1. `plan_id` matches `{slug}`
2. `steps` has at least 1 entry
3. Every step has unique `step_id`
4. Every step's `input_files` references files from prior steps or existing glob patterns
5. Every step has ≥1 `success_criteria`
6. All `status` values are `"pending"`

If validation fails: fix the issues and overwrite. If passes:

```
[ck:plan-json] ✓ plans/{slug}/plan.json written
Steps: {N}
Mode: {Fast | Hard}

Next: /ck:cook --json plans/{slug}/plan.json
```
