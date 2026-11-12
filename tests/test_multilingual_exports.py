import io
import zipfile

import pytest
from pypdf import PdfReader


@pytest.mark.parametrize("fmt", ["docx", "pdf"])
def test_mixed_vietnamese_japanese_exports_preserve_actual_unicode(api, fmt):
    project = api.project("QA multilingual export — not customer data")
    text = "Hướng dẫn 日本語テスト 価格 và quyền sử dụng"
    project = api.save(project, "A1", {"project": text, "org": "QA"})
    response = api.get(f"/projects/{project['id']}/package?format={fmt}")
    assert response.status_code == 200, response.text
    if fmt == "docx":
        with zipfile.ZipFile(io.BytesIO(response.content)) as document:
            xml = document.read("word/document.xml").decode("utf-8")
        assert text in xml
    else:
        reader = PdfReader(io.BytesIO(response.content))
        extracted = "\n".join(page.extract_text() for page in reader.pages)
        for phrase in ["Hướng dẫn", "日本語テスト", "価格", "quyền sử dụng"]:
            assert phrase in extracted
        assert "�" not in extracted
        embedded = []
        for page in reader.pages:
            for font in page["/Resources"]["/Font"].get_object().values():
                descriptor = font.get_object().get("/FontDescriptor")
                if descriptor:
                    embedded.append(descriptor.get_object().get("/FontFile2") is not None)
        assert any(embedded), "Unicode font must be embedded, not just named"


def test_vietnamese_only_pdf_renders_with_bundled_fonts(api):
    project = api.project("Quán cà phê Nắng — khai trương")
    project = api.save(project, "A1", {"project": "Khai trương chi nhánh 2", "org": "Quán cà phê Nắng"})
    for fmt in ("pdf", "client_pdf"):
        response = api.get(f"/projects/{project['id']}/package?format={fmt}")
        assert response.status_code == 200, response.text
        text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)
        assert "Khai trương chi nhánh 2" in text and "Quán cà phê Nắng" in text
        assert ("Phiếu nội bộ" in text) is (fmt == "pdf"), "Bản cho khách không có phần nội bộ"
