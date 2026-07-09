import base64
import io
import unittest
import zipfile

from document_parser import extract_docx_text


def make_docx_base64(text):
    xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class TestDocumentParser(unittest.TestCase):
    def test_extract_docx_text(self):
        content = make_docx_base64("Architecture 40%")

        self.assertEqual(extract_docx_text(content), "Architecture 40%")


if __name__ == "__main__":
    unittest.main()
