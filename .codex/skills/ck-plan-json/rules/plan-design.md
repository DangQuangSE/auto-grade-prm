# Plan JSON Design Rules

- **One goal per plan.** If the plan needs multiple unrelated features, split into separate plans.
- **Step atomicity.** Each step must produce at least one verifiable output (file created, test passing). If a step has no output_file, it's too abstract.
- **Input purity.** A step's `input_files` must reference files from prior steps or the existing codebase. Never reference files that don't exist yet.
- **Status lifecycle.** Only `pending` → `in_progress` → `completed`. Use `failed` only after 3 remediation cycles. `blocked` means needs human intervention.
- **Debug logs.** Every `failed` step must have at least one `debug_logs` entry. Empty debug_logs on failure = insufficient diagnosis.
- **Success criteria.** Must be verifiable by automation ("test passes", "file exists with pattern X"). Avoid "works correctly" or "looks good".
- **Max steps.** Keep under 15 steps. Beyond that, split into sub-plans.
- **current_step.** Always 1-indexed. Must never exceed len(steps). On completion, set to len(steps) + 1.
