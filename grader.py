from typing import Any, Dict, Optional

from providers import OpenRouterProvider
from rubric import DEFAULT_CRITERIA_TEXT, parse_rubric
from heuristics import fallback_heuristic_grade
from prompt_builder import build_grading_prompt


def apply_manual_testing_policy(
    report: Dict[str, Any], parsed_rubric: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Award full testing points while preserving the grader's written review."""
    breakdown = report.get("criteria_breakdown", {})
    score_adjustment = 0.0

    for name, rubric_item in parsed_rubric.items():
        if rubric_item.get("key") != "testing" or name not in breakdown:
            continue
        previous_score = float(breakdown[name]["score"])
        breakdown[name]["score"] = 10.0
        score_adjustment += (10.0 - previous_score) * rubric_item["weight"]

    if score_adjustment:
        report["overall_score"] = round(
            min(10.0, float(report["overall_score"]) + score_adjustment), 2
        )
    return report


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
        report = apply_manual_testing_policy(provider_result.data, parsed_rubric)
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
