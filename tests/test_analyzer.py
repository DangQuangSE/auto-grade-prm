import os
import tempfile
import unittest

from analyzer import analyze_flutter_project, validate_flutter_project


class TestAnalyzer(unittest.TestCase):
    def test_rejects_repository_without_pubspec(self):
        with tempfile.TemporaryDirectory() as project_path:
            os.makedirs(os.path.join(project_path, "lib"))
            error = validate_flutter_project(project_path)

        self.assertIn("thiếu pubspec.yaml", error)

    def test_rejects_pubspec_without_flutter_declaration(self):
        with tempfile.TemporaryDirectory() as project_path:
            os.makedirs(os.path.join(project_path, "lib"))
            with open(os.path.join(project_path, "pubspec.yaml"), "w", encoding="utf-8") as handle:
                handle.write("name: backend\ndependencies:\n  http: ^1.0.0\n")
            error = validate_flutter_project(project_path)

        self.assertIn("không khai báo Flutter", error)

    def test_rejects_flutter_project_without_dart_files(self):
        with tempfile.TemporaryDirectory() as project_path:
            os.makedirs(os.path.join(project_path, "lib"))
            with open(os.path.join(project_path, "pubspec.yaml"), "w", encoding="utf-8") as handle:
                handle.write("name: empty_app\ndependencies:\n  flutter:\n    sdk: flutter\n")
            error = validate_flutter_project(project_path)

        self.assertIn("không có file Dart", error)

    def test_accepts_flutter_project_with_nested_dart_file(self):
        with tempfile.TemporaryDirectory() as project_path:
            nested_path = os.path.join(project_path, "lib", "src")
            os.makedirs(nested_path)
            with open(os.path.join(project_path, "pubspec.yaml"), "w", encoding="utf-8") as handle:
                handle.write("name: valid_app\nflutter: {}\n")
            with open(os.path.join(nested_path, "app.dart"), "w", encoding="utf-8") as handle:
                handle.write("void main() {}\n")

            error = validate_flutter_project(project_path)

        self.assertIsNone(error)

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
