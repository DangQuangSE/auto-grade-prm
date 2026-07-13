import os
import tempfile
import unittest

from analyzer import analyze_flutter_project


class TestAnalyzer(unittest.TestCase):
    def test_reports_files_from_200_lines_with_structural_counts(self):
        with tempfile.TemporaryDirectory() as project_path:
            lib_path = os.path.join(project_path, "lib")
            os.makedirs(lib_path)
            content = "\n".join(
                [
                    "class ProductPage {",
                    "  Widget build(BuildContext context) => const SizedBox();",
                    "}",
                    "class ProductCard {}",
                ]
                + [f"// padding line {index}" for index in range(196)]
            )
            with open(
                os.path.join(lib_path, "product_page.dart"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(content)

            report = analyze_flutter_project(project_path)

        files = report["stats"]["files_over_200"]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["file"], os.path.join("lib", "product_page.dart"))
        self.assertEqual(files[0]["lines"], 200)
        self.assertEqual(files[0]["class_count"], 2)
        self.assertEqual(files[0]["build_method_count"], 1)


if __name__ == "__main__":
    unittest.main()
