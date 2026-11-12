from pathlib import Path
import json, io, zipfile
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

root=Path(__file__).resolve().parents[2]
questions=json.loads((root/'ai-video-production-os/backend/app/questions.json').read_text(encoding='utf-8'))
groups={
'CORE':('Thông tin chung','Câu hỏi chung dành cho mọi dự án.'),
'SNS':('Video ngắn / mạng xã hội','Chỉ trả lời nếu làm video ngắn hoặc đăng mạng xã hội.'),
'TVC':('Video quảng cáo','Chỉ trả lời nếu làm video quảng cáo trả phí.'),
'CORP':('Doanh nghiệp / sự kiện','Chỉ trả lời nếu làm video doanh nghiệp hoặc sự kiện.'),
'MOT':('Đồ họa chuyển động / màn hình trình chiếu','Chỉ trả lời nếu làm đồ họa chuyển động, dùng mẫu After Effects hoặc trình chiếu trên màn hình.'),
'GEN':('Nội dung tạo bằng AI','Chỉ trả lời nếu dự án có sử dụng AI để tạo hình ảnh hoặc video.'),
'LANG':('Ngôn ngữ và thuật ngữ','Trả lời khi cần quy định ngôn ngữ, cách đọc hoặc người duyệt nội dung.'),
'AUD':('Giọng đọc và âm thanh','Chỉ trả lời nếu video có giọng đọc, nhạc hoặc hiệu ứng âm thanh.')
}
fields={
'CORE-01':['Tên dự án / chiến dịch','Đơn vị yêu cầu','Người liên hệ và cách liên hệ'],
'CORE-06':['Loại video và số lượng từng loại','Thời lượng, khung hình và ngôn ngữ từng loại','Các bản cắt / tỷ lệ / ngôn ngữ có tính thêm video bàn giao không?'],
'CORE-09':['Ngôn ngữ chữ trên màn hình','Ngôn ngữ lời đọc (hoặc không dùng)','Ngôn ngữ phụ đề (hoặc không dùng)'],
'CORE-13':['Ngày, giờ cần bản xem trước','Ngày, giờ nhận bản chính thức','Ngày, giờ phát hành (nếu đã có)','Múi giờ'],
'CORE-14':['Người duyệt thông tin và kịch bản','Người duyệt hình ảnh và bản xem trước','Người duyệt bản cuối cùng','Cách liên hệ'],
'CORE-15':['Ngân sách dự kiến và đơn vị tiền tệ','Có cần báo giá trước không?','Số vòng chỉnh sửa mong muốn'],
'CORE-16':['Cách sản xuất mong muốn / cách không được dùng','Cho phép sử dụng AI tới mức nào?','Quyền sử dụng hình ảnh, nhạc, giọng và tài nguyên đang có','Người phụ trách bổ sung quyền hoặc tài liệu còn thiếu']
}
doc=Document()
section=doc.sections[0]
section.page_width=Cm(21); section.page_height=Cm(29.7)
section.top_margin=Cm(2); section.bottom_margin=Cm(2)
section.left_margin=Cm(2.2); section.right_margin=Cm(2.2)
normal=doc.styles['Normal']; normal.font.name='Arial'; normal.font.size=Pt(14)
normal.paragraph_format.line_spacing=1.35
normal.paragraph_format.space_after=Pt(10)
footer=section.footer.paragraphs[0]
footer.alignment=2
run=footer.add_run('Trang '); run.font.size=Pt(11)
fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); footer._p.append(fld)
footer.add_run(f' / {len(questions)}').font.size=Pt(11)

pdfmetrics.registerFont(TTFont('Questionnaire','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('QuestionnaireBold','C:/Windows/Fonts/arialbd.ttf'))
small=ParagraphStyle('note',fontName='Questionnaire',fontSize=12,leading=18,textColor=colors.HexColor('#46584e'),spaceAfter=12)
body=ParagraphStyle('body',fontName='Questionnaire',fontSize=14,leading=22,spaceAfter=8)
heading=ParagraphStyle('heading',fontName='QuestionnaireBold',fontSize=19,leading=28,textColor=colors.HexColor('#173e30'),spaceAfter=20)
story=[]
for index,q in enumerate(questions,1):
 group,note=groups[q['group']]
 if index>1:
  doc.add_page_break()
  story.append(PageBreak())
 p=doc.add_paragraph()
 r=p.add_run('BỘ CÂU HỎI DỰ ÁN VIDEO'); r.bold=True; r.font.size=Pt(12); r.font.color.rgb=RGBColor.from_string('3B6050')
 p=doc.add_paragraph(f'Câu {index}/{len(questions)} · {group}')
 for r in p.runs:r.font.size=Pt(12)
 p=doc.add_paragraph()
 r=p.add_run(q['label']); r.bold=True; r.font.size=Pt(19);r.font.color.rgb=RGBColor.from_string('173E30')
 p=doc.add_paragraph(note)
 for r in p.runs:r.font.size=Pt(12)
 p=doc.add_paragraph('Chưa rõ: ghi “Cần tư vấn”. Không liên quan: ghi “Không áp dụng”.')
 for r in p.runs:r.font.size=Pt(12)
 story.extend([Paragraph('BỘ CÂU HỎI DỰ ÁN VIDEO',small),Paragraph(f'Câu {index}/{len(questions)} · {escape(group)}',small),Paragraph(escape(q['label']),heading),Paragraph(escape(note),small),Paragraph('Chưa rõ: ghi “Cần tư vấn”. Không liên quan: ghi “Không áp dụng”.',small),Spacer(1,12)])
 labels=fields.get(q['code'],['Câu trả lời của bạn'])
 for label in labels:
  p=doc.add_paragraph();r=p.add_run(label);r.bold=True
  story.append(Paragraph(escape(label),body))
  n=2 if len(labels)<=3 else 1
  if len(labels)==1:n=7
  for _ in range(n):
   p=doc.add_paragraph('................................................................................................')
   p.paragraph_format.space_after=Pt(9)
   for r in p.runs:r.font.color.rgb=RGBColor.from_string('A2B1A6');r.font.size=Pt(12)
   story.append(Paragraph('................................................................................................',small))
   story.append(Spacer(1,5))
 doc.add_paragraph('Tài liệu / đường dẫn tham khảo (nếu có):')
 doc.add_paragraph('................................................................................................')
 story.extend([Spacer(1,10),Paragraph('Tài liệu / đường dẫn tham khảo (nếu có):',body),Paragraph('................................................................................................',small)])
doc_path=root/'BO-CAU-HOI-MOI-CAU-MOT-TRANG.docx'
pdf_path=root/'BO-CAU-HOI-MOI-CAU-MOT-TRANG.pdf'
doc.save(doc_path)
def footer_pdf(canvas,document):
 canvas.setFont('Questionnaire',10);canvas.setFillColor(colors.HexColor('#46584e'))
 canvas.drawRightString(A4[0]-62,35,f'Trang {document.page} / {len(questions)}')
SimpleDocTemplate(str(pdf_path),pagesize=A4,leftMargin=62,rightMargin=62,topMargin=52,bottomMargin=52,title='Bộ câu hỏi dự án video — mỗi câu một trang').build(story,onFirstPage=footer_pdf,onLaterPages=footer_pdf)
reader=PdfReader(pdf_path)
assert len(reader.pages)==len(questions),(len(reader.pages),len(questions))
with zipfile.ZipFile(doc_path) as archive:
 xml=archive.read('word/document.xml').decode()
 assert xml.count('w:type="page"')==len(questions)-1
for i,page in enumerate(reader.pages,1):
 assert f'Câu {i}/' in page.extract_text(),i
print(f'Created Word and PDF: {len(questions)} questions, exactly {len(reader.pages)} PDF pages; one question per page.')

