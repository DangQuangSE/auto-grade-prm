import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import AI_GRADING_UNAVAILABLE_MESSAGE, app
from grader import GradingUnavailableError


class TestAppContract(unittest.TestCase):
    def test_grade_returns_generic_503_when_all_ai_providers_fail(self):
        with patch("app.fetch_github_repo", return_value="sample"), patch(
            "app.validate_git_url"
        ), patch("app.validate_flutter_project", return_value=None), patch(
            "app.analyze_flutter_project", return_value={"stats": {}, "heuristics": {}}
        ), patch(
            "app.grade_project", side_effect=GradingUnavailableError("secret provider detail")
        ):
            response = TestClient(app).post(
                "/api/grade",
                json={"github_url": "https://github.com/example/flutter-app"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], AI_GRADING_UNAVAILABLE_MESSAGE)
        self.assertNotIn("secret provider detail", response.text)

    def test_grade_rejects_non_flutter_repository_before_grading(self):
        with tempfile.TemporaryDirectory() as project_path:
            with patch("app.fetch_github_repo", return_value=project_path), patch(
                "app.validate_git_url"
            ), patch("app.grade_project") as grade_project:
                response = TestClient(app).post(
                    "/api/grade",
                    json={"github_url": "https://github.com/example/not-flutter"},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("thiếu pubspec.yaml", response.json()["detail"])
        grade_project.assert_not_called()

    def test_provider_endpoint_does_not_expose_api_key(self):
        with patch.dict(
            "os.environ",
            {
                "OPENCODE_API_KEY": "sk-opencode-secret",
                "OPENCODE_MODEL": "mimo-v2.5-free",
                "OPENROUTER_API_KEY": "sk-secret-value",
                "OPENROUTER_MODEL": "tencent/hy3:free",
            },
            clear=True,
        ):
            response = TestClient(app).get("/api/provider")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["provider"], "opencode")
        self.assertEqual(data["model"], "mimo-v2.5-free")
        self.assertTrue(data["api_key_configured"])
        self.assertEqual(data["fallback_provider"], "openrouter")
        self.assertTrue(data["fallback_api_key_configured"])
        self.assertNotIn("sk-opencode-secret", str(data))
        self.assertNotIn("sk-secret-value", str(data))


if __name__ == "__main__":
    unittest.main()
