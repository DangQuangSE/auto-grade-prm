from typing import Any, Dict, Optional

from providers import OpenRouterProvider
from rubric import DEFAULT_CRITERIA_TEXT, parse_rubric
from heuristics import fallback_heuristic_grade
from prompt_builder import build_grading_prompt


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
