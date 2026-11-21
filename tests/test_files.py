from io import BytesIO
from zipfile import ZipFile

import openpyxl
import pytest
import xlwt
from docx import Document
from pypdf import PdfReader, PdfWriter

from backend.services.files import ValidationError, validate_upload


def test_pdf_validated(pdf_bytes):
    validated = validate_upload("cuestionario.pdf", pdf_bytes)
    assert validated.extension == ".pdf"
    assert len(validated.sha256) == 64
    assert validated.size == len(pdf_bytes)


@pytest.mark.parametrize("name,content", [
    ("payload.exe", b"content"), ("fake.pdf", b"not a pdf"), ("empty.pdf", b""),
    ("fake.xlsx", b"not an office file"), ("fake.docx", b"not an office file"),
    ("fake.xls", b"not an ole file"),
])
def test_invalid_files_rejected(name, content):
    with pytest.raises(ValidationError):
        validate_upload(name, content)


def test_size_limit(pdf_bytes, settings, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 20)
    with pytest.raises(ValidationError, match="no larger than"):
        validate_upload("large.pdf", pdf_bytes)


def test_encrypted_pdf_rejected(pdf_bytes):
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(pdf_bytes)))
    writer.encrypt("private")
    stream = BytesIO()
    writer.write(stream)
    with pytest.raises(ValidationError, match="password-protected"):
        validate_upload("secret.pdf", stream.getvalue())


def test_xlsx_all_sheets_preserve_values():
    book = openpyxl.Workbook()
    book.active.append(["1. Me gusta aprender", "Nunca", "Siempre", 0])
    book.create_sheet("Otra sección").append(["2. ¿Qué actividad disfruta?"])
    stream = BytesIO()
    book.save(stream)
    result = validate_upload("test.XLSX", stream.getvalue())
    assert "Nunca | Siempre | 0" in result.text
    assert "Otra sección" in result.text
    assert "2. ¿Qué actividad disfruta?" in result.text


def test_legacy_xls_supported():
    book = xlwt.Workbook()
    sheet = book.add_sheet("Preguntas")
    sheet.write(0, 0, "1. Describa una actividad")
    stream = BytesIO()
    book.save(stream)
    result = validate_upload("test.xls", stream.getvalue())
    assert "1. Describa una actividad" in result.text


def test_docx_paragraph_and_table_order():
    book = Document()
    book.add_paragraph("1. Primera pregunta")
    book.add_table(rows=1, cols=1).cell(0, 0).text = "A. Primera alternativa"
    book.add_paragraph("2. Segunda pregunta")
    stream = BytesIO()
    book.save(stream)
    result = validate_upload("test.docx", stream.getvalue())
    assert result.text.index("Primera pregunta") < result.text.index("Primera alternativa") < result.text.index("Segunda pregunta")


def test_empty_spreadsheet_rejected():
    stream = BytesIO()
    openpyxl.Workbook().save(stream)
    with pytest.raises(ValidationError, match="contains no"):
        validate_upload("empty.xlsx", stream.getvalue())


def test_office_disguised_as_other_type_is_rejected():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("unrelated.txt", "text")
    with pytest.raises(ValidationError, match="format"):
        validate_upload("wrong.docx", stream.getvalue())
