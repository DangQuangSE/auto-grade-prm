import json
import os
from typing import Any, Dict


def get_key_files_content(project_path: str) -> Dict[str, str]:
    file_contents = {}
    lib_path = os.path.join(project_path, "lib")
    if not os.path.exists(lib_path):
        return file_contents

    for root, dirs, files in os.walk(lib_path):
        dirs[:] = sorted(d for d in dirs if d not in {".dart_tool", "build"})
        for file_name in sorted(files):
            if not file_name.endswith(".dart") or len(file_contents) >= 12:
                continue
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, project_path)
            is_key = any(
                token in file_name.lower()
                for token in ["controller", "provider", "bloc", "model", "screen", "service", "main"]
            )
            if not is_key and len(file_contents) >= 5:
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
                file_contents[rel_path] = "".join(lines[:150]) + ("\n... [truncated]" if len(lines) > 150 else "")
            except OSError:
                continue

    pubspec_path = os.path.join(project_path, "pubspec.yaml")
    if os.path.exists(pubspec_path):
        try:
            with open(pubspec_path, "r", encoding="utf-8") as handle:
                file_contents["pubspec.yaml"] = handle.read()
        except OSError:
            pass

    return file_contents


def build_grading_prompt(
    project_path: str,
    analysis_report: Dict[str, Any],
    criteria_text: str,
    parsed_rubric: Dict[str, Dict[str, Any]],
) -> str:
    key_files = get_key_files_content(project_path)
    codebase_summary = "\n\n".join(f"--- FILE: {path} ---\n{content}" for path, content in key_files.items())
    schema_examples = {
        name: {
            "score": 0.0,
            "feedback": "Specific, evidence-based feedback citing the exact file(s) and code pattern observed",
            "suggestion": "Concrete fix: point to the exact file, describe the change, and include a short corrected Dart code snippet in a ```dart fence",
        }
        for name in parsed_rubric
    }
    weights_instruction = "\n".join(
        f"- {name}: {item['weight'] * 100:.2f}%" for name, item in parsed_rubric.items()
    )
    testing_criteria = [
        name for name, item in parsed_rubric.items() if item.get("key") == "testing"
    ]
    testing_instruction = (
        "\n".join(f'- "{name}"' for name in testing_criteria)
        if testing_criteria
        else "(none)"
    )

    return f"""
You are a senior Flutter/Dart code reviewer grading a student project.
Use the provided source excerpts and static analysis as evidence. Grade only against the user's criteria.

Source excerpts:
{codebase_summary}

Static analysis JSON:
{json.dumps(analysis_report, ensure_ascii=False, indent=2)}

User criteria template:
{criteria_text}

Weights to apply:
{weights_instruction}

Testing criteria that receive the manual-verification policy:
{testing_instruction}

Return exactly one JSON object with this schema:
{{
  "overall_score": <number from 0.0 to 10.0>,
  "criteria_breakdown": {json.dumps(schema_examples, ensure_ascii=False, indent=4)},
  "summary": "<concise Vietnamese summary of strengths and weaknesses>",
  "warnings": ["<file_name.dart>: <specific issue, its concrete impact, and the line count or code pattern that triggered it>"]
}}

Rules:
- Return valid JSON only.
- Use the exact criterion names shown in criteria_breakdown.
- Each criterion score must be from 0.0 to 10.0.
- For every criterion listed under "Testing criteria that receive the manual-verification policy", always assign score 10.0. Unit/widget tests are optional because functional testing may already have been completed manually, so missing automated test files must not reduce the score. Still write normal, evidence-based feedback and an actionable suggestion noting the absence or quality of automated tests; do not claim that automated tests exist without evidence.
- Follow Dart naming semantics when evaluating class names: public classes use PascalCase (for example `LoginPage`), while private classes may legally use one leading underscore followed by PascalCase (for example `_AppState` or `_LoginPageState`). A name matching `_?[A-Z][a-zA-Z0-9]*` is valid. If static analysis reports a leading-underscore private class as a PascalCase violation, treat it as a false positive: do not mention it as a defect, do not lower any criterion score for it, and do not suggest renaming it or adding `ignore_for_file: camel_case_types`.
- "feedback" must be specific and evidence-based: name the exact file (from the source excerpts or static analysis) and describe the actual code pattern found there. Avoid generic statements like "code could be better" without pointing to where.
- "suggestion" must give a concrete, actionable fix for that specific file/pattern: describe the refactor step and include a short corrected Dart code snippet (wrapped in a ```dart fence) showing the improved version.
- Every entry in "warnings" must start with the exact file name (e.g. "app_router.dart: ...") the issue was found in, followed by a concrete description of the problem (what pattern, how many lines/occurrences, why it matters). Never write a vague warning with no file name attached (e.g. do not write "Chưa có evidence về test tự động" alone — instead name which file(s) lack test coverage or state that no test files exist in the excerpts at all).
- Write "feedback", "suggestion", and "warnings" in Vietnamese.
- If evidence for a criterion is missing from the excerpts, say explicitly what needs manual review instead of inventing details.
""".strip()
