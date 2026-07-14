from typing import Any, Dict, Optional

from providers import OpenCodeProvider, OpenRouterProvider
from rubric import DEFAULT_CRITERIA_TEXT, parse_rubric
from prompt_builder import build_grading_prompt


class GradingUnavailableError(RuntimeError):
    """Raised when no configured AI provider can produce a grading report."""


def apply_manual_testing_policy(
    report: Dict[str, Any], parsed_rubric: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Award full testing points and deterministically recalculate the weighted total."""
    breakdown = report.get("criteria_breakdown", {})

    for name, rubric_item in parsed_rubric.items():
        if rubric_item.get("key") != "testing" or name not in breakdown:
            continue
        breakdown[name]["score"] = 10.0

    weighted_total = sum(
        float(breakdown.get(name, {}).get("score", 0.0)) * rubric_item["weight"]
        for name, rubric_item in parsed_rubric.items()
    )
    report["overall_score"] = round(min(10.0, max(0.0, weighted_total)), 2)
    return report


def grade_project(
    project_path: str,
    analysis_report: Dict[str, Any],
    criteria_text: Optional[str] = None,
) -> Dict[str, Any]:
    criteria_for_ai = criteria_text.strip() if criteria_text and criteria_text.strip() else DEFAULT_CRITERIA_TEXT
    parsed_rubric = parse_rubric(criteria_for_ai) or parse_rubric(DEFAULT_CRITERIA_TEXT)
    prompt = build_grading_prompt(project_path, analysis_report, criteria_for_ai, parsed_rubric)

    provider_results = []
    for provider in (OpenCodeProvider(), OpenRouterProvider()):
        provider_result = provider.generate_json(prompt)
        provider_results.append(provider_result)
        if not provider_result.ok:
            continue

        report = apply_manual_testing_policy(provider_result.data, parsed_rubric)
        report["provider"] = provider_result.provider
        report["model"] = provider_result.model
        report["grading_mode"] = "ai"
        return report

    raise GradingUnavailableError(
        "; ".join(f"{result.provider}: {result.error}" for result in provider_results)
    )


DEFAULT_RUBRIC = parse_rubric(DEFAULT_CRITERIA_TEXT)
