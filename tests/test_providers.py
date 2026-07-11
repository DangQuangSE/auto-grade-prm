import json
import os
import unittest
from unittest.mock import patch

from providers import OpenRouterProvider, ProviderError, get_provider_config, validate_grading_report


class TestOpenRouterProvider(unittest.TestCase):
    def test_config_reads_model_default(self):
        with patch.dict(os.environ, {}, clear=True):
            config = get_provider_config()

        self.assertEqual(config["provider"], "openrouter")
        self.assertEqual(config["model"], "tencent/hy3:free")
        self.assertFalse(config["api_key_configured"])

    def test_missing_api_key_returns_controlled_error(self):
        with patch.dict(os.environ, {"OPENROUTER_MODEL": "tencent/hy3:free"}, clear=True):
            provider = OpenRouterProvider()
            result = provider.generate_json("prompt")

        self.assertFalse(result.ok)
        self.assertEqual(result.provider, "openrouter")
        self.assertEqual(result.model, "tencent/hy3:free")
        self.assertIn("OPENROUTER_API_KEY", result.error)

    def test_parse_valid_openrouter_response(self):
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "overall_score": 8.25,
                                "criteria_breakdown": {
                                    "Structure": {
                                        "score": 8.0,
                                        "feedback": "Good module split.",
                                    }
                                },
                                "summary": "Solid project.",
                                "warnings": ["Review tests."],
                            }
                        )
                    }
                }
            ]
        }

        parsed = OpenRouterProvider.parse_response(json.dumps(body).encode("utf-8"))

        self.assertEqual(parsed["overall_score"], 8.25)
        self.assertEqual(parsed["criteria_breakdown"]["Structure"]["score"], 8.0)
        self.assertEqual(parsed["warnings"], ["Review tests."])

    def test_malformed_response_raises_controlled_error(self):
        body = {"choices": [{"message": {"content": "not-json"}}]}

        with self.assertRaises(ProviderError) as ctx:
            OpenRouterProvider.parse_response(json.dumps(body).encode("utf-8"))

        self.assertIn("valid JSON", str(ctx.exception))

    def test_http_failure_does_not_leak_api_key(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "sk-secret-value",
                "OPENROUTER_MODEL": "tencent/hy3:free",
            },
            clear=True,
        ):
            provider = OpenRouterProvider()
            with patch.object(provider, "_post", side_effect=ProviderError("network down")):
                result = provider.generate_json("prompt")

        self.assertFalse(result.ok)
        self.assertIn("network down", result.error)
        self.assertNotIn("sk-secret-value", result.error)

    def test_openrouter_uses_json_schema_response_format(self):
        response_format = OpenRouterProvider._response_format()

        self.assertEqual(response_format["type"], "json_schema")
        self.assertIn("json_schema", response_format)
        self.assertNotEqual(response_format["type"], "json_object")

    def test_response_format_requires_suggestion_per_criterion(self):
        response_format = OpenRouterProvider._response_format()
        criterion_schema = response_format["json_schema"]["schema"]["properties"]["criteria_breakdown"]["additionalProperties"]

        self.assertIn("suggestion", criterion_schema["required"])
        self.assertIn("suggestion", criterion_schema["properties"])

    def test_validate_grading_report_defaults_missing_suggestion(self):
        report = {
            "overall_score": 7.0,
            "criteria_breakdown": {
                "Structure": {"score": 7.0, "feedback": "Reasonable layout."}
            },
            "summary": "OK project.",
            "warnings": [],
        }

        validated = validate_grading_report(report)

        self.assertEqual(validated["criteria_breakdown"]["Structure"]["suggestion"], "")

    def test_validate_grading_report_rejects_non_string_suggestion(self):
        report = {
            "overall_score": 7.0,
            "criteria_breakdown": {
                "Structure": {"score": 7.0, "feedback": "Reasonable layout.", "suggestion": 123}
            },
            "summary": "OK project.",
            "warnings": [],
        }

        with self.assertRaises(ProviderError):
            validate_grading_report(report)


if __name__ == "__main__":
    unittest.main()
