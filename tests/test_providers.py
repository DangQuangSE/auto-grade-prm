import json
import os
import unittest
from unittest.mock import MagicMock, patch

from providers import OpenCodeProvider, OpenRouterProvider, ProviderError, get_provider_config, validate_grading_report


class TestOpenRouterProvider(unittest.TestCase):
    def test_config_reads_model_default(self):
        with patch.dict(os.environ, {}, clear=True):
            config = get_provider_config()

        self.assertEqual(config["provider"], "opencode")
        self.assertEqual(config["model"], "mimo-v2.5-free")
        self.assertFalse(config["api_key_configured"])
        self.assertEqual(config["fallback_provider"], "openrouter")
        self.assertEqual(config["fallback_model"], "openrouter/free")
        self.assertFalse(config["fallback_api_key_configured"])

    def test_opencode_normalizes_base_url_to_chat_completions(self):
        with patch.dict(
            os.environ,
            {"OPENCODE_BASE_URL": "https://opencode.ai/zen/v1/"},
            clear=True,
        ):
            provider = OpenCodeProvider()

        self.assertEqual(provider.provider, "opencode")
        self.assertEqual(provider.model, "mimo-v2.5-free")
        self.assertEqual(provider.base_url, "https://opencode.ai/zen/v1/chat/completions")
        self.assertEqual(provider._response_format(), {"type": "json_object"})

    def test_missing_api_key_returns_controlled_error(self):
        with patch.dict(os.environ, {"OPENROUTER_MODEL": "openrouter/free"}, clear=True):
            provider = OpenRouterProvider()
            result = provider.generate_json("prompt")

        self.assertFalse(result.ok)
        self.assertEqual(result.provider, "openrouter")
        self.assertEqual(result.model, "openrouter/free")
        self.assertIn("OPENROUTER_API_KEY", result.error)

    def test_provider_timeout_defaults_below_vercel_limit(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = OpenRouterProvider()

        self.assertEqual(provider.timeout, 90.0)
        self.assertLess(provider.timeout, 300)

    def test_provider_timeout_is_configurable_and_capped(self):
        with patch.dict(os.environ, {"OPENROUTER_TIMEOUT_SECONDS": "999"}, clear=True):
            provider = OpenRouterProvider()

        self.assertEqual(provider.timeout, 100.0)

    def test_primary_provider_timeout_is_configurable_and_capped(self):
        with patch.dict(os.environ, {"OPENCODE_TIMEOUT_SECONDS": "999"}, clear=True):
            provider = OpenCodeProvider()

        self.assertEqual(provider.timeout, 100.0)

    def test_http_error_only_surfaces_message_without_metadata(self):
        provider = OpenRouterProvider()
        details = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Provider is rate-limited.",
                    "metadata": {"raw": "large upstream payload"},
                }
            }
        )

        message = provider._format_http_error(429, details)

        self.assertEqual(message, "openrouter HTTP error 429: Provider is rate-limited.")
        self.assertNotIn("metadata", message)

    def test_invalid_provider_timeout_uses_default(self):
        with patch.dict(os.environ, {"AI_PROVIDER_TIMEOUT_SECONDS": "invalid"}, clear=True):
            provider = OpenRouterProvider()

        self.assertEqual(provider.timeout, 90.0)

    def test_post_uses_configured_provider_timeout(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"{}"
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "test-key", "AI_PROVIDER_TIMEOUT_SECONDS": "12"},
            clear=True,
        ):
            provider = OpenRouterProvider()
            with patch("urllib.request.urlopen", return_value=response) as urlopen:
                provider._post({"model": "test"})

        self.assertEqual(urlopen.call_args.kwargs["timeout"], 12.0)

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
