import base64
import io
import zipfile
import xml.etree.ElementTree as ET


class DocumentParseError(Exception):
    pass


WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_text(content_base64: str) -> str:
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except ValueError as exc:
        raise DocumentParseError("Invalid base64 document content.") from exc

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise DocumentParseError("The uploaded file is not a readable .docx document.") from exc

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise DocumentParseError("The .docx document XML could not be parsed.") from exc

    paragraphs = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{WORD_NAMESPACE}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{WORD_NAMESPACE}tab":
                parts.append("\t")
            elif node.tag == f"{WORD_NAMESPACE}br":
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)

    extracted = "\n".join(paragraphs).strip()
    if not extracted:
        raise DocumentParseError("No text was found in the .docx document.")
    return extracted


def decode_text_content(content_base64: str) -> str:
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except ValueError as exc:
        raise DocumentParseError("Invalid base64 text content.") from exc

    for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise DocumentParseError("The uploaded text file could not be decoded.")
