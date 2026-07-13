import unittest
from unittest.mock import patch

from grader import DEFAULT_CRITERIA_TEXT, apply_manual_testing_policy, grade_project, parse_rubric
from heuristics import get_heuristic_score_for_key
from prompt_builder import build_grading_prompt
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
    def test_manual_testing_policy_preserves_notes_and_adjusts_total(self):
        report = {
            "overall_score": 6.0,
            "criteria_breakdown": {
                "Architecture": {"score": 8.0, "feedback": "Good structure.", "suggestion": ""},
                "Testing": {"score": 4.0, "feedback": "No automated tests.", "suggestion": "Add tests."},
            },
        }
        rubric = parse_rubric("Architecture | 50%\nTesting | 50%")

        adjusted = apply_manual_testing_policy(report, rubric)

        self.assertEqual(adjusted["criteria_breakdown"]["Testing"]["score"], 10.0)
        self.assertEqual(adjusted["overall_score"], 9.0)
        self.assertEqual(adjusted["criteria_breakdown"]["Testing"]["feedback"], "No automated tests.")
        self.assertEqual(adjusted["criteria_breakdown"]["Testing"]["suggestion"], "Add tests.")

    def test_weighted_total_is_recalculated_instead_of_trusting_ai_total(self):
        scores = [9, 8, 7, 8, 9, 8, 9, 8, 7, 8, 8, 10]
        criteria = [
            ("Cấu trúc project", 10),
            ("Chất lượng code", 10),
            ("Tách widget", 10),
            ("Tách logic khỏi UI", 10),
            ("Quản lý state", 10),
            ("Navigation", 8),
            ("Model & dữ liệu", 8),
            ("Xử lý lỗi", 8),
            ("Responsive UI", 8),
            ("Tái sử dụng & constants", 6),
            ("Hiệu năng cơ bản", 6),
            ("Hoàn thiện & test", 6),
        ]
        criteria_text = "\n".join(f"{name} | {weight}%" for name, weight in criteria)
        report = {
            "overall_score": 7.8,
            "criteria_breakdown": {
                name: {"score": score, "feedback": "", "suggestion": ""}
                for (name, _weight), score in zip(criteria, scores)
            },
        }

        adjusted = apply_manual_testing_policy(report, parse_rubric(criteria_text))

        self.assertEqual(adjusted["overall_score"], 8.22)

    def test_testing_criterion_always_receives_full_heuristic_score(self):
        result = get_heuristic_score_for_key("testing", minimal_analysis())

        self.assertEqual(result["score"], 10.0)
        self.assertIn("optional for scoring", result["feedback"])

    @patch("prompt_builder.get_key_files_content", return_value={})
    def test_grading_prompt_requires_full_testing_score_but_keeps_feedback(self, _mock_files):
        rubric = parse_rubric("Architecture | 50%\nTesting and completion | 50%")

        prompt = build_grading_prompt("sample", minimal_analysis(), "criteria", rubric)

        self.assertIn('- "Testing and completion"', prompt)
        self.assertIn("always assign score 10.0", prompt)
        self.assertIn("Still write normal, evidence-based feedback", prompt)

    @patch("prompt_builder.get_key_files_content", return_value={})
    def test_grading_prompt_treats_private_dart_classes_as_valid(self, _mock_files):
        rubric = parse_rubric("Code quality | 100%")

        prompt = build_grading_prompt("sample", minimal_analysis(), "criteria", rubric)

        self.assertIn("private classes may legally use one leading underscore", prompt)
        self.assertIn("`_AppState` or `_LoginPageState`", prompt)
        self.assertIn("treat it as a false positive", prompt)
        self.assertIn("do not lower any criterion score", prompt)

    @patch("prompt_builder.get_key_files_content", return_value={})
    def test_grading_prompt_reviews_200_line_files_without_automatic_penalty(self, _mock_files):
        rubric = parse_rubric("Code quality | 100%")

        prompt = build_grading_prompt("sample", minimal_analysis(), "criteria", rubric)

        self.assertIn("never treat line count alone as a defect", prompt)
        self.assertIn("200-299 lines means", prompt)
        self.assertIn("A cohesive Bloc, Cubit, repository", prompt)
        self.assertIn("keep existing routes, callbacks, state ownership", prompt)

    def test_parse_rubric_normalizes_missing_weights(self):
        rubric = parse_rubric("Architecture\nState management\nTesting")

        self.assertEqual(set(rubric.keys()), {"Architecture", "State management", "Testing"})
        self.assertAlmostEqual(sum(item["weight"] for item in rubric.values()), 1.0)

    def test_parse_rubric_ignores_code_samples_and_uses_weight_table(self):
        text = """
Responsive UI
No overflow, works on many screen sizes
8%
SafeArea(
  child: SingleChildScrollView(
    child: Column(
      children: [...],
    ),
  ),
)
Code reuse
No duplicated widgets or constants
6%
"""
        rubric = parse_rubric(text)

        self.assertEqual(set(rubric.keys()), {"Responsive UI", "Code reuse"})
        self.assertNotIn("SafeArea(", rubric)
        self.assertNotIn("child: Column(", rubric)

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

        with patch("grader.OpenCodeProvider") as opencode_cls, patch("grader.OpenRouterProvider") as provider_cls:
            opencode_cls.return_value.generate_json.return_value = ProviderResult(
                ok=False, provider="opencode", model="mimo-v2.5-free", error="upstream error"
            )
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

        with patch("grader.OpenCodeProvider") as opencode_cls, patch("grader.OpenRouterProvider") as provider_cls:
            opencode_cls.return_value.generate_json.return_value = ProviderResult(
                ok=False, provider="opencode", model="mimo-v2.5-free", error="network down"
            )
            provider_cls.return_value.generate_json.return_value = provider_result
            report = grade_project("sample", minimal_analysis(), "Only custom criterion | 100%")

        self.assertEqual(report["grading_mode"], "heuristic")
        self.assertIn("opencode: network down", report["provider_error"])
        self.assertIn("openrouter: network down", report["provider_error"])
        self.assertNotIn("Only custom criterion", report["criteria_breakdown"])
        self.assertTrue(DEFAULT_CRITERIA_TEXT)
        for detail in report["criteria_breakdown"].values():
            self.assertIn("suggestion", detail)
            self.assertTrue(detail["suggestion"])


if __name__ == "__main__":
    unittest.main()
