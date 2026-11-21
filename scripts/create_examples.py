"""Generate wholly invented source fixtures. Never calls Gemini."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from openpyxl import Workbook
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
import xlwt

root = Path(__file__).resolve().parents[1] / "examples"
data = json.loads((root / "cuestionario_inventado.json").read_text(encoding="utf-8"))
lines = [data["titulo"], "Material inventado para pruebas de software. No es un test comercial."]
for item in data["items"]:
    lines.append(f"{item['numero']}. {item['enunciado']}")
    lines.append(f"Tipo: {item['tipo']}")
    lines.extend(f"{alt['valor']}: {alt['texto']}" for alt in item["alternativas"])
    if item["respuesta_correcta"] is not None:
        lines.append(f"Respuesta correcta indicada: {json.dumps(item['respuesta_correcta'], ensure_ascii=False)}")

word = Document()
for line in lines:
    word.add_paragraph(line)
word.save(root / "cuestionario_inventado.docx")
book = Workbook()
sheet = book.active
sheet.title = "Cuestionario"
sheet.column_dimensions["A"].width = 110
for line in lines:
    sheet.append([line])
book.save(root / "cuestionario_inventado.xlsx")
legacy = xlwt.Workbook()
sheet = legacy.add_sheet("Cuestionario")
sheet.col(0).width = 25000
for i, line in enumerate(lines):
    sheet.write(i, 0, line)
legacy.save(str(root / "cuestionario_inventado.xls"))
styles = getSampleStyleSheet()
story = []
for index, line in enumerate(lines):
    story.append(Paragraph(escape(line), styles["Title" if index == 0 else "BodyText"]))
    story.append(Spacer(1, 7))
SimpleDocTemplate(str(root / "cuestionario_inventado.pdf"), title=data["titulo"]).build(story)
print("Created invented PDF, DOCX, XLSX and XLS fixtures.")
