import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import openpyxl
import xlrd
from backend.config import settings
from docx import Document as WordDocument
from docx.table import Table
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls"}


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedFile:
    sha256: str
    extension: str
    text: str
    size: int


def _check_office_archive(data, required_member):
    with ZipFile(BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > 2000 or sum(m.file_size for m in members) > 30 * 1024 * 1024:
            raise ValidationError("The Office file exceeds the uncompressed content limit.")
        if required_member not in archive.namelist() or "[Content_Types].xml" not in archive.namelist():
            raise ValidationError("The file contents do not match the specified format.")


def _bounded_text(lines):
    parts, length = [], 0
    for line in lines:
        length += len(line) + 1
        if length > settings.MAX_EXTRACTED_CHARACTERS:
            raise ValidationError("The document contains too much text. Split it into smaller files.")
        parts.append(line)
    text = "\n".join(parts).strip()
    if not text:
        raise ValidationError("The document contains no text or populated cells.")
    return text


def _word_lines(document):
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                yield " | ".join(cell.text for cell in row.cells)
        elif block.text.strip():
            yield block.text


def _xlsx_lines(book):
    for sheet in book.worksheets:
        if (sheet.max_row or 0) > 5000 or (sheet.max_column or 0) > 100:
            raise ValidationError("Each worksheet can contain up to 5,000 rows and 100 columns.")
        has_content = False
        for row in sheet.iter_rows(values_only=True):
            if any(value is not None and str(value).strip() for value in row):
                if not has_content:
                    yield f"Hoja: {sheet.title}"
                    has_content = True
                yield " | ".join("" if value is None else str(value) for value in row)


def _xls_lines(book):
    for sheet in book.sheets():
        if sheet.nrows > 5000 or sheet.ncols > 100:
            raise ValidationError("Each worksheet can contain up to 5,000 rows and 100 columns.")
        has_content = False
        for row_number in range(sheet.nrows):
            row = sheet.row_values(row_number)
            if any(str(value).strip() for value in row):
                if not has_content:
                    yield f"Hoja: {sheet.name}"
                    has_content = True
                yield " | ".join(str(value) for value in row)


def validate_upload(filename: str, data: bytes):
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValidationError("Unsupported format. Upload a PDF, DOCX, XLSX, or XLS file.")
    if not data or len(data) > settings.MAX_UPLOAD_BYTES:
        raise ValidationError(f"The file must not be empty and must be no larger than {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    text = ""
    try:
        if extension == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise ValidationError("The file contents are not a valid PDF.")
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise ValidationError("The PDF is password-protected. Upload an unprotected copy.")
            if not 1 <= len(reader.pages) <= settings.MAX_PDF_PAGES:
                raise ValidationError(f"The PDF must contain between 1 and {settings.MAX_PDF_PAGES} pages.")
        elif extension == ".docx":
            _check_office_archive(data, "word/document.xml")
            text = _bounded_text(_word_lines(WordDocument(BytesIO(data))))
        elif extension == ".xlsx":
            _check_office_archive(data, "xl/workbook.xml")
            book = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
            try:
                text = _bounded_text(_xlsx_lines(book))
            finally:
                book.close()
        else:
            if not data.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
                raise ValidationError("The file contents are not a valid XLS file.")
            book = xlrd.open_workbook(file_contents=data, on_demand=True)
            try:
                text = _bounded_text(_xls_lines(book))
            finally:
                book.release_resources()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("Unable to open the file. Make sure it is not damaged or password-protected.") from exc
    return ValidatedFile(hashlib.sha256(data).hexdigest(), extension, text, len(data))
