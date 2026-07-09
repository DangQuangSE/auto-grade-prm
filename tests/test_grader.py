import unittest
from unittest.mock import patch

from grader import DEFAULT_CRITERIA_TEXT, grade_project, parse_rubric
from providers import ProviderResult


def minimal_analysis():
    return {
        "structure": {
            "folder_structure_score": 70,
            "details": ["Layered structure found."],
            "has_models": True,
        },
        "stats": {
            "large_files": [],
            "naming_violations": [],
        },
        "heuristics": {
            "api_calls_in_build": [],
            "state_management": ["provider"],
            "navigation_patterns": ["lib/main.dart"],
            "error_handling_count": 1,
            "responsive_widgets_used": ["Expanded"],
            "pubspec_details": {"has_assets": True},
        },
    }


class TestGrader(unittest.TestCase):
    def test_parse_rubric_normalizes_missing_weights(self):
        rubric = parse_rubric("Architecture\nState management\nTesting")

        self.assertEqual(set(rubric.keys()), {"Architecture", "State management", "Testing"})
        self.assertAlmostEqual(sum(item["weight"] for item in rubric.values()), 1.0)

    def test_provider_success_uses_ai_metadata(self):
        provider_result = ProviderResult(
            ok=True,
            provider="openrouter",
            model="tencent/hy3:free",
            data={
                "overall_score": 9.0,
                "criteria_breakdown": {
                    "Architecture": {"score": 9.0, "feedback": "Clear structure."}
                },
                "summary": "Strong submission.",
                "warnings": [],
            },
        )

        with patch("grader.OpenRouterProvider") as provider_cls:
            provider_cls.return_value.generate_json.return_value = provider_result
            report = grade_project("sample", minimal_analysis(), "Architecture | 100%")

        self.assertEqual(report["grading_mode"], "ai")
        self.assertEqual(report["provider"], "openrouter")
        self.assertEqual(report["model"], "tencent/hy3:free")

    def test_provider_failure_falls_back_to_default_template(self):
        provider_result = ProviderResult(
            ok=False,
            provider="openrouter",
            model="tencent/hy3:free",
            error="network down",
        )

        with patch("grader.OpenRouterProvider") as provider_cls:
            provider_cls.return_value.generate_json.return_value = provider_result
            report = grade_project("sample", minimal_analysis(), "Only custom criterion | 100%")

        self.assertEqual(report["grading_mode"], "heuristic")
        self.assertEqual(report["provider_error"], "network down")
        self.assertNotIn("Only custom criterion", report["criteria_breakdown"])
        self.assertTrue(DEFAULT_CRITERIA_TEXT)


if __name__ == "__main__":
    unittest.main()
