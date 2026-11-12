"""Export saved intake answers, one question per page. Never invent missing values."""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from pypdf import PdfReader
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from manage import ENV, load_env
load_env()
from app.db import make_engine, make_session_factory
from app.models import Project, Answer
from app.questionnaire import QUESTIONS

engine = make_engine(ENV['DATABASE_URL'])
with make_session_factory(engine)() as db:
    project = db.scalars(select(Project).order_by(Project.updated_at.desc())).first()
    if not project:
        raise SystemExit('No project exists; no customer answers exported.')
    name, status = project.name, project.status
    rows = db.scalars(select(Answer).where(Answer.project_id == project.id)).all()
    saved = [{'code': row.question_code, 'scope': row.scope_id, 'value': row.value,
              'status': row.status, 'locator': row.evidence_locator} for row in rows]
engine.dispose()

pdfmetrics.registerFont(TTFont('Answers', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('AnswersBold', 'C:/Windows/Fonts/arialbd.ttf'))
small = ParagraphStyle('small', fontName='Answers', fontSize=12, leading=18, textColor=colors.HexColor('#4d6159'), spaceAfter=14)
title = ParagraphStyle('title', fontName='AnswersBold', fontSize=19, leading=28, spaceAfter=22)
body = ParagraphStyle('body', fontName='Answers', fontSize=15, leading=24, spaceAfter=16)
story = []
for index, question in enumerate(QUESTIONS, 1):
    if index > 1:
        story.append(PageBreak())
    story.append(Paragraph('CÂU TRẢ LỜI DỰ ÁN — ' + escape(name), small))
    story.append(Paragraph(f'BẢN NHÁP · {len(saved)} câu trả lời đã lưu · Câu {index}/{len(QUESTIONS)}', small))
    story.append(Paragraph(escape(question['label']), title))
    matching = [row for row in saved if row['code'] == question['code']]
    if not matching:
        story.append(Paragraph('Chưa có câu trả lời được lưu.', body))
    for answer in matching:
        value = answer['value'] if isinstance(answer['value'], str) else json.dumps(answer['value'], ensure_ascii=False, indent=2)
        story.append(Paragraph('Phạm vi: ' + escape(answer['scope'] or 'Thông tin chung'), small))
        story.append(Paragraph(escape(value or 'Chưa có nội dung.').replace('\n', '<br/>'), body))
        state = 'Đã xác nhận' if answer['status'] == 'CONFIRMED' else 'Chưa được xác nhận'
        story.append(Paragraph(state, small))
        if answer['locator']:
            story.append(Paragraph('Vị trí nguồn: ' + escape(answer['locator']), small))
    if not saved:
        story.append(Spacer(1, 18))
        story.append(Paragraph('Ứng dụng chưa có câu trả lời được lưu cho dự án này. Hãy nhập nội dung và bấm “Lưu câu trả lời” để xuất lại bản có dữ liệu.', small))

destination = ROOT.parent / 'CAU-TRA-LOI-DU-AN.pdf'
def footer(canvas, document):
    canvas.setFont('Answers', 10)
    canvas.drawRightString(A4[0] - 60, 32, f'Trang {document.page}')
SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=60, rightMargin=60,
                  topMargin=55, bottomMargin=55).build(story, onFirstPage=footer, onLaterPages=footer)
reader = PdfReader(destination)
assert reader.pages and 'DRAFT' not in reader.pages[0].extract_text()
print(json.dumps({'file': destination.name, 'saved_answers': len(saved), 'pages': len(reader.pages)}, ensure_ascii=True))
