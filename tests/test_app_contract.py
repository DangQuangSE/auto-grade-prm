import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


class TestAppContract(unittest.TestCase):
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
