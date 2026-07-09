import os
import tempfile
import unittest
from unittest.mock import patch

from env_loader import load_dotenv


class TestEnvLoader(unittest.TestCase):
    def test_loads_env_file_without_overriding_existing_values(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write("OPENROUTER_MODEL=tencent/hy3:free\n")
            handle.write("OPENROUTER_API_KEY='from-file'\n")
            path = handle.name

        try:
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "existing"}, clear=True):
                load_dotenv(path)

                self.assertEqual(os.environ["OPENROUTER_MODEL"], "tencent/hy3:free")
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "existing")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
