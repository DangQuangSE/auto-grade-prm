import json
import os
import re
from typing import Any, Dict, Optional

from providers import OpenRouterProvider


HEURISTIC_MAPPING = [
    {"keywords": ["structure", "folder", "architecture", "cau truc"], "key": "structure"},
    {"keywords": ["readability", "clean code", "doc", "chat luong"], "key": "readability"},
    {"keywords": ["widget", "build"], "key": "widgets"},
    {"keywords": ["logic", "service", "controller", "repository"], "key": "logic"},
    {"keywords": ["state", "provider", "bloc", "riverpod", "getx"], "key": "state"},
    {"keywords": ["navigation", "route"], "key": "navigation"},
    {"keywords": ["model", "data", "json"], "key": "models"},
    {"keywords": ["error", "exception", "try-catch", "validate"], "key": "errors"},
    {"keywords": ["responsive", "overflow", "layout"], "key": "responsive"},
    {"keywords": ["reuse", "constant", "duplicate"], "key": "reusability"},
    {"keywords": ["resource", "asset", "pubspec"], "key": "resources"},
    {"keywords": ["performance", "rebuild"], "key": "performance"},
    {"keywords": ["extend", "extensible", "maintain"], "key": "extensibility"},
    {"keywords": ["convention", "naming", "pascal", "camel", "snake"], "key": "convention"},
    {"keywords": ["test", "testing"], "key": "testing"},
]

DEFAULT_CRITERIA_TEXT = """Project structure | 10%
Readable code | 10%
Widget decomposition | 10%
Separation of UI and logic | 10%
State management | 10%
Navigation | 8%
Data models | 8%
Error handling | 8%
Responsive UI | 8%
Code reuse | 6%
Resource management | 6%
Basic performance | 6%
Extensibility | 6%
Coding convention | 6%
Testing or manual verification | 6%"""


def _map_heuristic_key(name: str) -> str:
    normalized = name.lower()
    for item in HEURISTIC_MAPPING:
        if any(keyword in normalized for keyword in item["keywords"]):
            return item["key"]
    return "readability"


def _extract_weight(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1)) / 100.0


def _clean_criterion_name(text: str) -> str:
    text = re.sub(r"^\s*[-*]\s+", "", text)
    text = re.sub(r"^\s*\d+[\.)]\s*", "", text)
    text = re.sub(r"\s*\(?\d+(?:\.\d+)?\s*%\)?\s*$", "", text)
    return text.strip(" :-\t")


def parse_rubric(criteria_text: Optional[str]) -> Optional[Dict[str, Dict[str, Any]]]:
    if not criteria_text or not criteria_text.strip():
        return None

    raw_items = []
    for raw_line in criteria_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if set(line.replace("|", "").strip()) <= {"-"}:
            continue
        if any(header in lowered for header in ["criteria", "rubric", "weight"]) and "|" in line:
            continue

        if "|" in line:
            parts = [part.strip() for part in line.split("|") if part.strip()]
            if not parts:
                continue
            name = _clean_criterion_name(parts[0])
            weight = None
            for part in reversed(parts):
                weight = _extract_weight(part)
                if weight is not None:
                    break
        else:
            name = _clean_criterion_name(line)
            weight = _extract_weight(line)

        if name:
            raw_items.append({"name": name, "weight": weight})

    if not raw_items:
        return None

    explicit_weight = sum(item["weight"] for item in raw_items if item["weight"] is not None)
    missing = [item for item in raw_items if item["weight"] is None]
    if missing:
        remaining = max(0.0, 1.0 - explicit_weight)
        even_weight = remaining / len(missing) if remaining > 0 else 1.0 / len(raw_items)
        for item in missing:
            item["weight"] = even_weight

    total_weight = sum(item["weight"] for item in raw_items)
    if total_weight <= 0:
        return None

    rubric = {}
    for item in raw_items:
        normalized_weight = item["weight"] / total_weight
        rubric[item["name"]] = {
            "weight": normalized_weight,
            "key": _map_heuristic_key(item["name"]),
        }

    return rubric


def get_heuristic_score_for_key(key: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    if key == "structure":
        struct_score = analysis["structure"]["folder_structure_score"] / 10.0
        details = analysis["structure"].get("details") or []
        return {
            "score": struct_score,
            "feedback": f"Folder structure score is {struct_score * 10:.0f}%. {'; '.join(details)}",
        }

    if key == "readability":
        large_files_count = len(analysis["stats"]["large_files"])
        score = max(4.0, 10.0 - min(3.0, large_files_count * 1.0))
        return {
            "score": score,
            "feedback": f"Found {large_files_count} large files over 300 lines.",
        }

    if key == "widgets":
        score = 9.0
        for large_file in analysis["stats"]["large_files"]:
            path = large_file["file"].lower()
            if "screen" in path or "widget" in path:
                score -= 1.0
        return {
            "score": max(5.0, score),
            "feedback": "Large screen/widget files may need decomposition into smaller widgets.",
        }

    if key == "logic":
        violations = len(analysis["heuristics"]["api_calls_in_build"])
        return {
            "score": max(4.0, 7.0 - violations * 3.0),
            "feedback": f"Found {violations} possible API calls inside build methods.",
        }

    if key == "state":
        managers = analysis["heuristics"]["state_management"]
        return {
            "score": 9.0 if managers else 6.0,
            "feedback": f"Detected state management: {', '.join(managers)}" if managers else "No common state management package detected.",
        }

    if key == "navigation":
        count = len(analysis["heuristics"]["navigation_patterns"])
        return {
            "score": 8.5 if count else 6.0,
            "feedback": f"Detected navigation usage in {count} files.",
        }

    if key == "models":
        has_models = analysis["structure"]["has_models"]
        return {
            "score": 9.0 if has_models else 6.0,
            "feedback": "Model structure detected." if has_models else "No clear model folder or model structure detected.",
        }

    if key == "errors":
        count = analysis["heuristics"]["error_handling_count"]
        return {
            "score": min(10.0, 5.0 + count * 0.5),
            "feedback": f"Detected {count} try/catch blocks.",
        }

    if key == "responsive":
        widgets = analysis["heuristics"]["responsive_widgets_used"]
        return {
            "score": min(10.0, 5.0 + len(widgets) * 1.5),
            "feedback": f"Responsive/layout widgets used: {', '.join(widgets) if widgets else 'none detected'}.",
        }

    if key == "resources":
        has_assets = analysis["heuristics"]["pubspec_details"].get("has_assets", False)
        return {
            "score": 9.0 if has_assets else 6.0,
            "feedback": "Assets are configured in pubspec.yaml." if has_assets else "No assets configuration detected in pubspec.yaml.",
        }

    if key == "performance":
        violations = len(analysis["heuristics"]["api_calls_in_build"])
        return {
            "score": max(5.0, 9.0 - violations * 2.0),
            "feedback": "Performance risk increases when API calls or heavy work happen in build methods.",
        }

    if key == "convention":
        violations = len(analysis["stats"]["naming_violations"])
        return {
            "score": max(4.0, 10.0 - violations * 0.5),
            "feedback": f"Detected {violations} naming convention issues.",
        }

    if key == "testing":
        return {
            "score": 6.0,
            "feedback": "Static analysis cannot fully verify unit/widget tests; review test coverage manually.",
        }

    if key == "reusability":
        return {
            "score": 7.5,
            "feedback": "Review repeated widgets, constants, and shared utilities for reuse opportunities.",
        }

    if key == "extensibility":
        return {
            "score": 7.5,
            "feedback": "Extensibility depends on clear module boundaries and separation of responsibilities.",
        }

    return {"score": 7.0, "feedback": "General heuristic evaluation."}


def fallback_heuristic_grade(
    analysis: Dict[str, Any],
    parsed_rubric: Optional[Dict[str, Dict[str, Any]]] = None,
    provider_error: Optional[str] = None,
) -> Dict[str, Any]:
    rubric_to_use = parsed_rubric or parse_rubric(DEFAULT_CRITERIA_TEXT)
    scores = {}
    total_score = 0.0
    total_weight = 0.0

    for name, item in rubric_to_use.items():
        result = get_heuristic_score_for_key(item["key"], analysis)
        scores[name] = result
        total_score += result["score"] * item["weight"]
        total_weight += item["weight"]

    final_score = (total_score / total_weight) if total_weight > 0 else 0.0
    warnings = list(analysis["heuristics"]["api_calls_in_build"]) + list(analysis["stats"]["naming_violations"])
    if provider_error:
        warnings.insert(0, f"AI provider failed; default-template heuristic fallback was used. Error: {provider_error}")

    report = {
        "overall_score": round(final_score, 2),
        "criteria_breakdown": scores,
        "summary": "Automatic heuristic grading was used. Configure OpenRouter successfully for AI-based rubric review.",
        "warnings": warnings,
        "provider": "openrouter",
        "model": None,
        "grading_mode": "heuristic",
    }
    if provider_error:
        report["provider_error"] = provider_error

    return report


def get_key_files_content(project_path: str) -> Dict[str, str]:
    file_contents = {}
    lib_path = os.path.join(project_path, "lib")
    if not os.path.exists(lib_path):
        return file_contents

    for root, dirs, files in os.walk(lib_path):
        dirs[:] = [d for d in dirs if d not in {".dart_tool", "build"}]
        for file_name in files:
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
        name: {"score": 0.0, "feedback": "Evidence-based feedback for this criterion"}
        for name in parsed_rubric
    }
    weights_instruction = "\n".join(
        f"- {name}: {item['weight'] * 100:.2f}%" for name, item in parsed_rubric.items()
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

Return exactly one JSON object with this schema:
{{
  "overall_score": <number from 0.0 to 10.0>,
  "criteria_breakdown": {json.dumps(schema_examples, ensure_ascii=False, indent=4)},
  "summary": "<concise Vietnamese summary of strengths and weaknesses>",
  "warnings": ["<specific issue or risk>"]
}}

Rules:
- Return valid JSON only.
- Use the exact criterion names shown in criteria_breakdown.
- Each criterion score must be from 0.0 to 10.0.
- Base feedback on the static analysis and source excerpts. If evidence is missing, say what needs manual review.
""".strip()


def grade_project(
    project_path: str,
    analysis_report: Dict[str, Any],
    criteria_text: Optional[str] = None,
) -> Dict[str, Any]:
    criteria_for_ai = criteria_text.strip() if criteria_text and criteria_text.strip() else DEFAULT_CRITERIA_TEXT
    parsed_rubric = parse_rubric(criteria_for_ai) or parse_rubric(DEFAULT_CRITERIA_TEXT)
    prompt = build_grading_prompt(project_path, analysis_report, criteria_for_ai, parsed_rubric)

    provider = OpenRouterProvider()
    provider_result = provider.generate_json(prompt)
    if provider_result.ok:
        report = provider_result.data
        report["provider"] = provider_result.provider
        report["model"] = provider_result.model
        report["grading_mode"] = "ai"
        return report

    default_rubric = parse_rubric(DEFAULT_CRITERIA_TEXT)
    report = fallback_heuristic_grade(
        analysis_report,
        default_rubric,
        provider_error=provider_result.error,
    )
    report["provider"] = provider_result.provider
    report["model"] = provider_result.model
    return report


DEFAULT_RUBRIC = parse_rubric(DEFAULT_CRITERIA_TEXT)
