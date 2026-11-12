"""Typeset a real saved-answer PDF with restrained editorial layout."""
from pathlib import Path
from datetime import datetime
import hashlib, json, sys, re
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader
from sqlalchemy import select

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from manage import ENV,load_env
load_env()
from app.db import make_engine,make_session_factory
from app.models import Project,Answer
from app.questionnaire import QUESTIONS

GROUPS={
'CORE':('01','Thông tin dự án','Thông tin chung để thống nhất yêu cầu và phạm vi thực hiện.'),
'SNS':('02','Video ngắn & mạng xã hội','Chỉ cần bổ sung khi dự án có video ngắn hoặc nội dung mạng xã hội.'),
'TVC':('03','Video quảng cáo','Bổ sung thông tin cho quảng cáo trả phí và các yêu cầu phát hành.'),
'CORP':('04','Doanh nghiệp & sự kiện','Bổ sung thông tin cho video doanh nghiệp, phỏng vấn hoặc sự kiện.'),
'MOT':('05','Đồ họa & trình chiếu','Bổ sung thông tin cho đồ họa chuyển động, mẫu dựng và màn hình trình chiếu.'),
'GEN':('06','Hình ảnh & video AI','Bổ sung khi dự án có sử dụng AI để tạo hình ảnh hoặc chuyển động.'),
'LANG':('07','Ngôn ngữ & thuật ngữ','Thống nhất cách dùng từ, cách đọc và người duyệt ngôn ngữ.'),
'AUD':('08','Giọng đọc & âm thanh','Bổ sung khi video có lời đọc, nhạc nền hoặc hiệu ứng âm thanh.')
}
FIELDS={
'CORE-01':['Tên dự án / chiến dịch','Đơn vị yêu cầu','Người liên hệ'],
'CORE-06':['Loại video và số lượng','Thời lượng, khung hình và ngôn ngữ','Quy ước tính các phiên bản bàn giao'],
'CORE-09':['Ngôn ngữ trên màn hình','Ngôn ngữ lời đọc','Ngôn ngữ phụ đề'],
'CORE-13':['Hạn bản xem trước','Hạn bản chính thức','Ngày phát hành và múi giờ'],
'CORE-14':['Người duyệt và vai trò','Đầu mối liên hệ'],
'CORE-15':['Ngân sách và đơn vị tiền tệ','Phạm vi báo giá / số vòng chỉnh sửa'],
'CORE-16':['Phương thức sản xuất','Phạm vi cho phép dùng AI','Quyền tài nguyên và người phụ trách']
}
KEYS={'on_screen':'Chữ trên màn hình','voiceover':'Lời đọc','subtitles':'Phụ đề','preview_due':'Bản xem trước','final_due':'Bản chính thức','publish_date':'Ngày phát hành','timezone':'Múi giờ','approver_name':'Người duyệt','approval_role':'Vai trò','contact':'Liên hệ','budget_status':'Tình trạng ngân sách','amount':'Ngân sách','currency':'Tiền tệ','revision_rounds':'Số vòng chỉnh sửa','production_mode':'Phương thức sản xuất','rights_status':'Tình trạng quyền sử dụng','rights_notes':'Ghi chú về quyền sử dụng','ai_consent':'Cho phép dùng AI','variant_policy':'Quy ước tính phiên bản'}
VALUES={'vi':'Tiếng Việt','ja':'Tiếng Nhật','en':'Tiếng Anh','CONFIRMED':'Đã xác nhận','CONSULTATION':'Cần tư vấn','HYBRID':'Kết hợp nhiều phương thức','GENERATIVE_AI':'Tạo bằng AI','NO_AI':'Không sử dụng AI','FOOTAGE':'Sử dụng video có sẵn','AE':'After Effects','CLEARED':'Đã có quyền sử dụng','PLANNED':'Có kế hoạch bổ sung quyền','UNKNOWN':'Chưa xác định','PM':'Quản lý dự án','ADMIN':'Quản trị','ACCOUNT':'Phụ trách khách hàng'}
STATE={'CONFIRMED':'Đã xác nhận','PROPOSED_FROM_SOURCE':'Gợi ý từ tài liệu · Chưa xác nhận','ANSWERED_UNCONFIRMED':'Đã nhập · Chưa xác nhận','UNKNOWN':'Chưa xác định','NEEDS_CONSULTATION':'Cần tư vấn','NOT_APPLICABLE':'Không áp dụng','CONFLICTED':'Cần làm rõ'}
engine=make_engine(ENV['DATABASE_URL'])
with make_session_factory(engine)() as db:
    p=db.scalars(select(Project).order_by(Project.updated_at.desc())).first()
    if not p: raise SystemExit('No project to export.')
    project={'name':p.name,'revision':p.revision,'status':p.status}
    answers=[{'code':a.question_code,'scope':a.scope_id,'value':a.value,'status':a.status,'locator':a.evidence_locator} for a in db.scalars(select(Answer).where(Answer.project_id==p.id).order_by(Answer.question_code,Answer.scope_id))]
engine.dispose()
pdfmetrics.registerFont(TTFont('Editorial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('EditorialBold','C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('EditorialItalic','C:/Windows/Fonts/ariali.ttf'))
W,H=A4; M=48; CW=W-M*2
INK=colors.HexColor('#19372f'); TEAL=colors.HexColor('#256653')
TEXT=colors.HexColor('#2b3c34'); MUTED=colors.HexColor('#596b60')
LINE=colors.HexColor('#d6dfd7'); PALE=colors.HexColor('#f3f6f1')
path=ROOT.parent/'HO-SO-DU-AN-VIDEO-CHUYEN-NGHIEP.pdf'
c=canvas.Canvas(str(path),pagesize=A4,pageCompression=1)
c.setTitle('Hồ sơ yêu cầu sản xuất video — '+project['name'])
c.setAuthor('Hồ sơ dự án')
c.setSubject('Câu hỏi và câu trả lời đã lưu; mỗi câu hỏi một trang')

def para(text,x,top,width,size=14,leading=None,font='Editorial',color=TEXT):
    style=ParagraphStyle('p',fontName=font,fontSize=size,leading=leading or size*1.48,textColor=color,spaceAfter=0,splitLongWords=True)
    p=Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    _,height=p.wrap(width,H)
    p.drawOn(c,x,top-height)
    return top-height

def icon(x,y,group):
    c.setStrokeColor(TEAL); c.setFillColor(PALE); c.setLineWidth(1.15)
    c.roundRect(x,y,40,40,9,fill=1,stroke=0)
    c.setFillColor(TEAL)
    if group in {'SNS','TVC','GEN'}:
        c.roundRect(x+8,y+11,24,19,3,fill=0,stroke=1)
        p=c.beginPath();p.moveTo(x+18,y+15);p.lineTo(x+18,y+25);p.lineTo(x+26,y+20);p.close()
        c.drawPath(p,fill=1,stroke=0)
    elif group=='AUD':
        for i,h in enumerate([9,18,25,15,7]):
            c.line(x+10+i*5,y+20-h/2,x+10+i*5,y+20+h/2)
    else:
        c.roundRect(x+12,y+7,18,26,2,fill=0,stroke=1)
        for dy,length in [(25,9),(20,12),(15,10)]:
            c.line(x+15,y+dy,x+15+length,y+dy)

def value_text(value):
    if value is None:return 'Chưa cung cấp'
    if isinstance(value,bool):return 'Có' if value else 'Không'
    if isinstance(value,str):return VALUES.get(value,value)
    if isinstance(value,list):return ', '.join(value_text(v) for v in value) or 'Không sử dụng'
    if isinstance(value,dict):
        if isinstance(value.get('items'),list):
            out=[]
            for i,item in enumerate(value['items'],1):
                if not isinstance(item,dict):continue
                out.append(f"{i}. {item.get('category','')} · {item.get('quantity','')} video · {item.get('duration_seconds','')} giây · {item.get('aspect_ratio','')} · {value_text(item.get('language'))}")
                for variant in item.get('variants',[]):
                    out.append('   '+variant.get('label','Phiên bản')+(' — tính thêm file giao' if variant.get('counts_as_separate') else ' — không tính thêm file giao'))
            out.append('Quy ước: '+str(value.get('variant_policy','Chưa cung cấp')))
            return '\n'.join(out)
        return '\n'.join(KEYS.get(k,k)+': '+value_text(v) for k,v in value.items() if k not in {'id'})
    return str(value)

def chrome(index,q,continued=False):
    group_num,group,note=GROUPS[q['group']]
    c.setFillColor(colors.white);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(TEAL);c.rect(M,H-55,4,15,fill=1,stroke=0)
    para('HỒ SƠ YÊU CẦU SẢN XUẤT VIDEO',M+14,H-40,CW-74,10.5,14,'EditorialBold',TEAL)
    para(project['name'],M,H-77,CW-100,13,18,'EditorialBold',INK)
    c.setStrokeColor(LINE);c.setLineWidth(.7);c.line(M,H-94,W-M,H-94)
    icon(W-M-40,H-85,q['group'])
    para('PHẦN '+group_num+'  /  '+group.upper(),M,H-119,CW,10.5,15,'EditorialBold',TEAL)
    c.setFillColor(colors.HexColor('#d8e5db'));c.setFont('EditorialBold',48);c.drawString(M,H-193,f'{index:02}')
    top=para(q['label']+(' — tiếp theo' if continued else ''),M+78,H-153,CW-78,21,29,'EditorialBold',INK)
    top=min(top-18,H-240)
    top=para(note,M,top,CW,12,18,'Editorial',MUTED)
    c.setStrokeColor(LINE);c.line(M,top-14,W-M,top-14)
    c.setStrokeColor(LINE);c.line(M,55,W-M,55)
    para('Bản thu thập thông tin · Phiên bản '+str(project['revision']),M,42,CW-100,9.5,13,'Editorial',MUTED)
    c.setFillColor(MUTED);c.setFont('Editorial',10);c.drawRightString(W-M,30,f'{c.getPageNumber():02}  /  Câu {index:02}')
    return top-38

layout=[]
for index,q in enumerate(QUESTIONS,1):
    y=chrome(index,q)
    matching=[a for a in answers if a['code']==q['code']]
    if matching:
        for a in matching:
            state=STATE.get(a['status'],'Chưa xác nhận')
            y=para(state.upper(),M,y,CW,10.5,16,'EditorialBold',TEAL)-16
            if a['scope']:
                y=para('Phạm vi: '+a['scope'],M,y,CW,11,16,'Editorial',MUTED)-12
            lines=value_text(a['value']).split('\n')
            for line in lines:
                style=ParagraphStyle('measure',fontName='Editorial',fontSize=14,leading=21)
                item=Paragraph(escape(line) or ' ',style)
                height=item.wrap(CW-32,H)[1]
                if y-height<125:
                    c.showPage();y=chrome(index,q,True)
                y=para(line,M+16,y,CW-32,14,21)-9
            y-=15
    else:
        c.setFillColor(PALE);c.roundRect(M,y-33,CW,33,5,fill=1,stroke=0)
        para('CHƯA CÓ CÂU TRẢ LỜI ĐƯỢC LƯU',M+13,y-10,CW-26,10.5,15,'EditorialBold',MUTED)
        y-=65
        labels=FIELDS.get(q['code'],['Nội dung trả lời'])
        available=y-145
        row_height=min(120,available/len(labels))
        if len(labels)==1: row_height=available
        for label in labels:
            para(label,M,y,CW,13,19,'EditorialBold',TEXT)
            c.setStrokeColor(LINE);c.setLineWidth(.5)
            line_y=y-40
            while line_y>y-row_height+10:
                c.line(M,line_y,W-M,line_y)
                line_y-=27
            y-=row_height
    if y>142:
        c.setFillColor(PALE);c.roundRect(M,83,CW,55,5,fill=1,stroke=0)
        para('Tài liệu / đường dẫn tham chiếu',M+12,124,CW-24,11.5,16,'EditorialBold',TEXT)
        refs=' · '.join(a['locator'] for a in matching if a.get('locator'))
        para(refs or 'Chưa cung cấp',M+12,105,CW-24,11,15,'Editorial',MUTED)
    layout.append({'question':q['code'],'page':c.getPageNumber(),'saved':len(matching)})
    c.showPage()
c.save()
reader=PdfReader(path)
for page in reader.pages:
    assert page.extract_text().strip()
assert len(reader.pages)>=len(QUESTIONS)
metadata={'file':path.name,'project':project,'questions':len(QUESTIONS),'saved_answers':len(answers),'pdf_pages':len(reader.pages),'layout':layout,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
proof=ROOT/'runtime'/'professional-pdf';proof.mkdir(parents=True,exist_ok=True)
(proof/'layout.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'file':path.name,'questions':len(QUESTIONS),'pages':len(reader.pages),'saved_answers':len(answers)},ensure_ascii=True))

