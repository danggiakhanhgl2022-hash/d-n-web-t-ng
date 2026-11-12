import hashlib
import io
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .questionnaire import (CATALOG, QUESTIONS, SECTIONS, answer_rows, answer_text, canonical, delivery_matrix,
                            scope_text, _label)

HERE = Path(__file__).resolve().parent
BRAND = json.loads((HERE / "brand.json").read_text(encoding="utf-8"))
STATUS_TEXT = {"CONFIRMED": "Đã xác nhận", "ANSWERED_UNCONFIRMED": "Chờ xác nhận", "PROPOSED_FROM_SOURCE": "Gợi ý từ tài liệu",
               "NEEDS_CONSULTATION": "Cần tư vấn", "CONFLICTED": "Có mâu thuẫn", "UNKNOWN": "Chưa xác định",
               "NOT_APPLICABLE": "Không áp dụng", "UNANSWERED": "Chưa trả lời"}
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]")


def _state(decision, snapshot):
    approved = decision and decision.get("decision") == "APPROVED"
    state = "APPROVED SNAPSHOT" if approved else "DRAFT — CHƯA DUYỆT"
    if snapshot and snapshot.get("historical"):
        state += " — HISTORICAL"
    return state, bool(approved)


def _sheet(payload, state):
    project = payload["project"]
    title = f"# {project['name']}\n\nTrạng thái: {state}\n\nKhách hàng: {project['customer']}\nPhiên bản: {project['revision']}\n"
    by_code = {q["code"]: q for q in payload.get("questionnaire_definition", QUESTIONS) if isinstance(q, dict) and "code" in q}
    sheet = title + "\n## Câu trả lời và bằng chứng\n"
    for a in payload["answers"]:
        q = by_code.get(a["question_code"]) or CATALOG.get(a["question_code"]) or {"label": "Câu hỏi của bộ cũ"}
        activity = "ĐANG ÁP DỤNG" if a.get("applicable", True) else "LỊCH SỬ — KHÔNG ÁP DỤNG: " + a.get("inactive_reason", "Nhánh đã đổi")
        sheet += (f"\n### {a['question_code']} — {q['label']}\n\nTrạng thái: {STATUS_TEXT.get(a['status'], a['status'])} · {activity}\n\n"
                  f"{answer_text(a['question_code'], a['value']) or '—'}\n\n"
                  f"Nguồn: {a.get('source_id') or 'Trả lời trực tiếp'}; vị trí: {a.get('evidence_locator') or '—'}\n"
                  f"Người xác nhận: {a.get('confirmed_by') or 'CHƯA CÓ'}\n")
    return title, sheet


def package_files(payload, decision=None, snapshot=None):
    answers = payload["answers"]
    validation = payload["validation"]
    state, _ = _state(decision, snapshot)
    title, sheet = _sheet(payload, state)
    matrix = delivery_matrix(answers)
    gaps = title + "\n" + "\n".join(f"- {b['question_code']}: {b['message']}" for b in validation["blockers"])
    if not validation["blockers"]:
        gaps += "\nKhông còn blocker theo policy stage01; không có nghĩa đã được phê duyệt.\n"
    if validation.get("clarifications"):
        gaps += "\n\n## Cần làm rõ\n" + "\n".join(f"- {c['question_code']}: {c['message']}" for c in validation["clarifications"])
    acceptance = title + "\n## Tiêu chí đánh giá truy về yêu cầu\n\n| RequirementID | Nguồn | Giá trị cần tuân thủ | Phép kiểm |\n| --- | --- | --- | --- |\n"
    for a in answers:
        if a["status"] != "CONFIRMED" or a.get("applicable") is False:
            continue
        if a["question_code"] == "D1" and isinstance(a["value"], dict) and isinstance(a["value"].get("rows"), list):
            for i, row in enumerate(a["value"]["rows"], 1):
                line = answer_text("D1", {"rows": [row]}).replace("Yêu cầu: ", "").replace("|", "\\|")
                acceptance += f"| REQ-D1-{i:02d} | D1 dòng {i} / revision {a['revision']} | {line} | Xem cảnh tương ứng trong bản dựng |\n"
            continue
        value = answer_text(a["question_code"], a["value"]).replace("|", "\\|").replace("\n", " · ")
        acceptance += f"| REQ-{a['question_code']} | {a['question_code']} / revision {a['revision']} | {value} | Đối chiếu với đầu ra và bản nguồn đã xác nhận |\n"
    rights = {code: next((a for a in answers if a["question_code"] == code and not a.get("scope_id")), None) for code in ("A17", "A18", "E10")}
    files = {
        "OUTPUT/FOLDER_THONG_TIN/00_BAT_DAU_TU_DAY.md": title + "\nĐọc Answer Sheet, ma trận bàn giao, báo cáo thiếu và tiêu chí trước khi duyệt.\nKhông dùng bản DRAFT cho sản xuất chính thức.\n",
        "OUTPUT/FOLDER_THONG_TIN/01_THONG_TIN_DU_AN.md": title,
        "OUTPUT/FOLDER_THONG_TIN/02_TRA_LOI_DA_XAC_NHAN.md": sheet,
        "OUTPUT/FOLDER_THONG_TIN/03_BRIEF_CHUAN_HOA.json": canonical({"project": payload["project"], "confirmed_requirements": [a for a in answers if a["status"] == "CONFIRMED" and a.get("applicable") is not False]}),
        "OUTPUT/FOLDER_THONG_TIN/03_BRIEF_CHUAN_HOA.md": sheet,
        "OUTPUT/FOLDER_THONG_TIN/04_MA_TRAN_VIDEO_BAN_GIAO.json": canonical(matrix),
        "OUTPUT/FOLDER_THONG_TIN/04_MA_TRAN_VIDEO_BAN_GIAO.md": title + "\n## Ma trận bàn giao\n\n```json\n" + json.dumps(matrix, ensure_ascii=False, indent=2) + "\n```\n",
        "OUTPUT/FOLDER_THONG_TIN/05_TAI_NGUYEN_VA_QUYEN_SU_DUNG.json": canonical({"sources": payload["sources"], "rights_answers": rights, "note": "Khách tự khai (CLAIMED) chưa phải đã xác minh quyền dùng."}),
        "OUTPUT/FOLDER_THONG_TIN/06_THIEU_MAU_THUAN_CAN_HOI.md": gaps,
        "OUTPUT/FOLDER_THONG_TIN/07_TIEU_CHI_DANH_GIA_DUNG_SAI.md": acceptance,
        "OUTPUT/FOLDER_THONG_TIN/08_NGUON_VA_PHAN_HOI.json": canonical({"sources": payload["sources"], "feedback": payload.get("feedback", [])}),
        "OUTPUT/FOLDER_THONG_TIN/09_PHIEU_DUYET_THONG_TIN.json": canonical(decision or {"decision": "PENDING", "actor_id": None}),
        "REVIEW/00_XEM_VA_DUYET.md": title + "\n## Xem và duyệt\n- Mở OUTPUT/FOLDER_THONG_TIN/ để đối chiếu nguồn, câu trả lời và số lượng video.\n- Kiểm blocker trong 06_THIEU_MAU_THUAN_CAN_HOI.md.\n- Duyệt trong ứng dụng bằng tài khoản có quyền; sửa JSON không tạo Approval Event.\n",
        "REVIEW/CHECKLIST.md": "# Checklist\n\n- [ ] Khung hình A7 khớp độ phân giải E1\n- [ ] Các mốc A14 hợp lý và chưa qua\n- [ ] Bảng D1 không còn dòng mâu thuẫn\n- [ ] Quyền tài nguyên (A18, E10) đã xác minh\n- [ ] Không còn blocker\n- [ ] Đã xem hash/phiên bản trước quyết định\n",
        "REVIEW/PHAN_HOI.json": canonical(payload.get("feedback", [])),
        "APPROVAL/decision.json": canonical(decision or {"decision": "PENDING", "actor_id": None}),
        "INPUT/source-index.json": canonical(payload["sources"]),
        "WORK/intake-contract.json": canonical(payload),
        "SNAPSHOT/snapshot.json": canonical(snapshot or {"status": "DRAFT", "snapshot_id": None}),
    }
    manifest = {"schema_version": "3.0", "stage_id": "01", "gate_id": "STAGE_01_INFORMATION", "stage_version": payload["project"]["revision"], "status": state, "snapshot": snapshot, "approval": decision, "delivery_matrix": matrix, "artifacts": []}
    for name, content in files.items():
        data = content.encode("utf-8")
        manifest["artifacts"].append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    files["OUTPUT/FOLDER_THONG_TIN/manifest.json"] = canonical(manifest)
    files["stage_manifest.json"] = canonical(manifest)
    return files, sheet


# ---------------------------------------------------------------- DOCX

def _docx(payload, decision, snapshot, files):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor
    colors = BRAND["colors"]
    rgb = lambda h: RGBColor.from_string(h.lstrip("#").upper())
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Carlito"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "MS Gothic")
    normal.font.size = Pt(10.5)
    state, _ = _state(decision, snapshot)
    project = payload["project"]
    head = doc.add_paragraph()
    run = head.add_run(BRAND["studio_name"].upper())
    run.bold, run.font.size, run.font.color.rgb = True, Pt(9), rgb(colors["primary"])
    t = doc.add_heading(BRAND.get("tagline", "Phiếu tiếp nhận"), 0)
    doc.add_paragraph(f"{project['name']} · {project.get('customer') or 'Chưa có khách hàng'} · Phiên bản {project['revision']} · {state}")
    answers = {a["question_code"]: a for a in payload["answers"] if not a.get("scope_id")}
    applicable = set(payload["validation"].get("applicable_codes", []))
    for section in SECTIONS:
        codes = [q["code"] for q in QUESTIONS if q["section"] == section["id"] and (q["code"] in applicable or q["code"] in answers)]
        if not codes:
            continue
        h = doc.add_heading(f"{section['part']} · {section['title']}", 1)
        for code in codes:
            q = CATALOG[code]
            a = answers.get(code)
            p = doc.add_paragraph()
            r = p.add_run(f"{code}  ")
            r.bold, r.font.color.rgb = True, rgb(colors["primary"])
            r = p.add_run(q["label"])
            r.bold = True
            status = STATUS_TEXT.get(a["status"], a["status"]) if a else "Chưa trả lời"
            r = p.add_run(f"   [{status}]")
            r.font.size, r.font.color.rgb = Pt(9), rgb(colors["muted"])
            for label, text in (answer_rows(code, a["value"]) if a else []):
                line = doc.add_paragraph(style="List Bullet")
                if label:
                    lr = line.add_run(label + ": ")
                    lr.font.color.rgb = rgb(colors["muted"])
                line.add_run(text)
    legacy = [a for a in payload["answers"] if a["question_code"] not in CATALOG]
    if legacy:
        doc.add_heading("Câu trả lời của bộ câu hỏi cũ (lịch sử)", 1)
        for a in legacy:
            doc.add_paragraph(f"{a['question_code']}: {answer_text(a['question_code'], a['value'])}")
    doc.add_heading("Thiếu sót và cần làm rõ", 1)
    for line in files["OUTPUT/FOLDER_THONG_TIN/06_THIEU_MAU_THUAN_CAN_HOI.md"].splitlines()[6:]:
        if line.strip():
            doc.add_paragraph(line.lstrip("#- "))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- PDF

def _register_fonts(need_cjk):
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fonts = HERE / "fonts"
    names = pdfmetrics.getRegisteredFontNames()
    if "Body" not in names:
        override = os.getenv("PDF_FONT_PATH", "")
        regular = Path(override) if override and Path(override).is_file() else fonts / "Carlito-Regular.ttf"
        if not regular.is_file():
            raise RuntimeError("PDF_FONT_UNAVAILABLE: Thiếu phông chữ trong backend/app/fonts hoặc PDF_FONT_PATH.")
        pdfmetrics.registerFont(TTFont("Body", str(regular)))
        bold = fonts / "Carlito-Bold.ttf"
        italic = fonts / "Carlito-Italic.ttf"
        pdfmetrics.registerFont(TTFont("Body-Bold", str(bold if bold.is_file() else regular)))
        pdfmetrics.registerFont(TTFont("Body-Italic", str(italic if italic.is_file() else regular)))
        display = fonts / "Lora-Variable.ttf"
        pdfmetrics.registerFont(TTFont("Display", str(display if display.is_file() else regular)))
        addMapping("Body", 0, 0, "Body")
        addMapping("Body", 1, 0, "Body-Bold")
        addMapping("Body", 0, 1, "Body-Italic")
        addMapping("Body", 1, 1, "Body-Bold")
    if need_cjk and "IntakeCJK" not in pdfmetrics.getRegisteredFontNames():
        cjk = next((p for p in [os.getenv("PDF_CJK_FONT_PATH", ""), "C:/Windows/Fonts/msgothic.ttc",
                                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                                "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"] if p and Path(p).is_file()), None)
        if not cjk:
            raise RuntimeError("PDF_CJK_FONT_UNAVAILABLE: Cần PDF_CJK_FONT_PATH cho nội dung Nhật/Trung.")
        pdfmetrics.registerFont(TTFont("IntakeCJK", cjk, subfontIndex=0))


def _rich(text):
    """Chuỗi an toàn cho Paragraph; chữ Nhật/Trung dùng phông riêng."""
    out = escape(str(text)).replace("\n", "<br/>")
    return re.sub(r"([\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]+)", r'<font name="IntakeCJK">\1</font>', out)


def _pdf(payload, decision, snapshot, files, client=False):
    from reportlab.lib import colors as rl
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rlcanvas
    from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, NextPageTemplate,
                                    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

    c = {k: rl.HexColor(v) for k, v in BRAND["colors"].items()}
    every_text = json.dumps(payload, ensure_ascii=False)
    _register_fonts(bool(CJK.search(every_text)))
    state, approved = _state(decision, snapshot)
    project = payload["project"]
    validation = payload["validation"]
    answers = {a["question_code"]: a for a in payload["answers"] if not a.get("scope_id")}
    applicable = set(validation.get("applicable_codes", []))
    W, H = A4
    margin = 18 * mm

    def style(name, **kw):
        base = dict(fontName="Body", fontSize=10, leading=14, textColor=c["ink"], alignment=TA_LEFT, wordWrap="CJK")
        base.update(kw)
        return ParagraphStyle(name, **base)

    s_eyebrow = style("eyebrow", fontName="Body-Bold", fontSize=8, leading=10, textColor=c["primary"])
    s_h1 = style("h1", fontName="Display", fontSize=34, leading=40)
    s_h2 = style("h2", fontName="Display", fontSize=20, leading=25)
    s_sub = style("sub", fontSize=10.5, leading=15, textColor=c["muted"])
    s_q = style("q", fontName="Body-Bold", fontSize=11, leading=15)
    s_code = style("code", fontName="Body-Bold", fontSize=8.5, leading=11, textColor=c["primary_ink"], alignment=1)
    s_label = style("label", fontSize=8.5, leading=12, textColor=c["muted"])
    s_value = style("value", fontSize=10, leading=14)
    s_answer = style("answer", fontSize=10.5, leading=14.5, textColor=c["ink"])
    s_empty = style("empty", fontName="Body-Italic", fontSize=9.5, leading=13, textColor=c["muted"])
    s_small = style("small", fontSize=8.5, leading=12, textColor=c["muted"])
    s_kpi_v = style("kpiv", fontName="Display", fontSize=17, leading=21)
    s_kpi_l = style("kpil", fontName="Body-Bold", fontSize=7.5, leading=10, textColor=c["muted"])
    s_cover_h = style("coverh", fontName="Display", fontSize=46, leading=50, textColor=c["paper"])
    s_cover_p = style("coverp", fontName="Display", fontSize=19, leading=24, textColor=c["paper"])
    s_cover_l = style("coverl", fontName="Body-Bold", fontSize=7.5, leading=10, textColor=c["line"])
    s_cover_v = style("coverv", fontName="Display", fontSize=19, leading=23, textColor=c["paper"])
    s_cover_s = style("covers", fontSize=9, leading=13, textColor=c["line"])

    status_color = {"CONFIRMED": c["good"], "ANSWERED_UNCONFIRMED": c["warn"], "PROPOSED_FROM_SOURCE": c["warn"],
                    "NEEDS_CONSULTATION": c["accent"], "CONFLICTED": c["danger"]}

    def P(text, st):
        return Paragraph(_rich(text), st)

    class Bar(Flowable):
        def __init__(self, ratio, width=W - 2 * margin, height=7):
            super().__init__()
            self.ratio, self.width, self.height = max(0, min(1, ratio)), width, height
            self.track = c["line"]

        def wrap(self, *_):
            return self.width, self.height

        def draw(self):
            cv = self.canv
            cv.setFillColor(self.track)
            cv.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
            if self.ratio:
                cv.setFillColor(c["primary"])
                cv.roundRect(0, 0, max(self.height, self.width * self.ratio), self.height, self.height / 2, stroke=0, fill=1)

    class NumberedCanvas(rlcanvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for state_dict in self._saved:
                self.__dict__.update(state_dict)
                if self._pageNumber > 1:
                    self.setFont("Body", 8)
                    self.setFillColor(c["muted"])
                    self.drawRightString(W - margin, 12 * mm, f"Trang {self._pageNumber} / {total}")
                super().showPage()
            super().save()

    def paper(cv):
        cv.setFillColor(c["paper"])
        cv.rect(0, 0, W, H, stroke=0, fill=1)

    def glow(cv, x, y, radius, color, strength=0.5, steps=70):
        cv.setFillColor(color)
        for i in range(steps):
            k = 1 - i / steps
            cv.setFillAlpha(strength / steps * 1.6)
            cv.circle(x, y, radius * k, stroke=0, fill=1)
        cv.setFillAlpha(1)

    def on_cover(cv, doc):
        cv.saveState()
        cv.setFillColor(c["ink"])
        cv.rect(0, 0, W, H, stroke=0, fill=1)
        glow(cv, W - 10 * mm, H - 30 * mm, 120 * mm, c["primary"], 0.9)
        glow(cv, 10 * mm, 30 * mm, 90 * mm, c["accent"], 0.7)
        cv.setFillColor(c["primary"])
        cv.circle(W - 52 * mm, H - 62 * mm, 16 * mm, stroke=0, fill=1)
        cv.setFillColor(c["paper"])
        cv.rect(margin, 26 * mm, 26 * mm, 1.6, stroke=0, fill=1)
        cv.setFont("Body", 8)
        cv.setFillColor(c["paper"])
        cv.setFillAlpha(0.6)
        cv.drawString(margin, 16 * mm, f"{BRAND['studio_name']} · Xuất lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        cv.restoreState()

    def on_page(cv, doc):
        cv.saveState()
        paper(cv)
        cv.setFillColor(c["primary"])
        cv.rect(0, H - 3, W, 3, stroke=0, fill=1)
        cv.setFont("Body-Bold", 8)
        cv.setFillColor(c["ink"])
        cv.drawString(margin, H - 12 * mm, BRAND["studio_name"].upper())
        cv.setFont("Body", 8)
        cv.setFillColor(c["muted"])
        name = project["name"] if not CJK.search(project["name"]) else "Dự án"
        cv.drawRightString(W - margin, H - 12 * mm, f"{name[:60]} · v{project['revision']}")
        cv.setStrokeColor(c["line"])
        cv.setLineWidth(0.6)
        cv.line(margin, 17 * mm, W - margin, 17 * mm)
        cv.drawString(margin, 12 * mm, "Bản cho khách" if client else ("Đã duyệt" if approved else "Bản nháp – chưa duyệt"))
        cv.restoreState()

    doc = BaseDocTemplate(io.BytesIO(), pagesize=A4, title=project["name"], author=BRAND["studio_name"],
                          leftMargin=margin, rightMargin=margin, topMargin=22 * mm, bottomMargin=22 * mm)
    body = Frame(margin, 22 * mm, W - 2 * margin, H - 44 * mm, id="body", leftPadding=0, rightPadding=0,
                 topPadding=0, bottomPadding=0)
    cover = Frame(margin, 32 * mm, W - 2 * margin, H - 60 * mm, id="cover", leftPadding=0, rightPadding=0)
    doc.addPageTemplates([PageTemplate("cover", [cover], onPage=on_cover), PageTemplate("body", [body], onPage=on_page)])

    def chip(text, bg, fg=None, st=None):
        t = Table([[P(text, st or style("chip", fontName="Body-Bold", fontSize=8, leading=10, textColor=fg or c["primary_ink"], alignment=1))]])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                               ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                               ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
        return t

    root = lambda code, field: (answers.get(code, {}).get("value") or {}).get(field) if isinstance(answers.get(code, {}).get("value"), dict) else None

    def field_label(code, field, ident):
        f = next((x for x in CATALOG[code]["fields"] if x["id"] == field), None)
        if not f or ident is None:
            return None
        if isinstance(ident, list):
            return ", ".join(_label(f.get("options", []), x) for x in ident)
        return _label(f.get("options", []), ident)

    story = []
    inner_w0 = W - 2 * margin
    # ---------------- Bìa
    story += [Spacer(1, 72 * mm), P(BRAND.get("tagline", "Phiếu tiếp nhận yêu cầu video").upper(), s_eyebrow), Spacer(1, 5 * mm),
              P(project["name"], s_cover_h), Spacer(1, 3 * mm),
              P(project.get("customer") or "Chưa ghi tên khách hàng", s_cover_p), Spacer(1, 12 * mm)]
    total_req = len(validation.get("required_codes", [])) or 1
    done = validation.get("completion", 0)
    meta = [[P("PHIÊN BẢN", s_cover_l), P("TRẠNG THÁI", s_cover_l), P("HOÀN THÀNH", s_cover_l)],
            [P(f"v{project['revision']}", s_cover_v),
             P("Đã duyệt" if approved else ("Bản cho khách" if client else "Bản nháp"), s_cover_v),
             P(f"{done}%", s_cover_v)]]
    mt = Table(meta, colWidths=[(W - 2 * margin) / 3] * 3)
    mt.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, c["paper"]), ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    bar = Bar(done / 100)
    bar.track = rl.Color(1, 1, 1, alpha=0.18)
    story += [mt, Spacer(1, 4 * mm), bar, Spacer(1, 3 * mm),
              P(f"{len(validation.get('required_codes', []))} câu bắt buộc · {len(validation.get('blockers', []))} việc còn mở"
                + (" · " + state if not client else ""), s_cover_s)]
    contact = answers.get("A2")
    if contact:
        story += [Spacer(1, 10 * mm), P("NGƯỜI TRAO ĐỔI", s_cover_l), P(answer_text("A2", contact["value"]).replace("\n", " · "), style("cv", textColor=c["paper"]))]
    story += [NextPageTemplate("body"), PageBreak()]

    # ---------------- Tóm tắt
    matrix = delivery_matrix(payload["answers"])
    a14 = answers.get("A14", {}).get("value") if answers.get("A14") else None
    final = (answer_rows("A14", a14) if a14 else [])
    final_text = next((t for l, t in final if l.startswith("Cần bản chính thức")), "—")
    kpis = [("SỐ VIDEO", str(matrix.get("total_base") or "—")),
            ("KHUNG HÌNH", ", ".join(matrix["items"][0]["aspect_ratios"]) if matrix.get("items") else "—"),
            ("THỜI LƯỢNG", field_label("A8", "length", root("A8", "length")) or "—"),
            ("MỤC ĐÍCH", field_label("A3", "v", root("A3", "v")) or "—"),
            ("BẢN CHÍNH THỨC", final_text),
            ("NGÂN SÁCH", field_label("A15", "range", root("A15", "range")) or "—")]
    cw = (W - 2 * margin - 2 * 4 * mm) / 3
    cells = [[Table([[P(l, s_kpi_l)], [P(v, s_kpi_v)]], colWidths=[cw - 8 * mm]) for l, v in kpis[i:i + 3]] for i in (0, 3)]
    grid = Table(cells, colWidths=[cw + 4 * mm] * 3, rowHeights=None)
    grid.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c["surface"]), ("BOX", (0, 0), (-1, -1), 0.6, c["line"]),
                              ("INNERGRID", (0, 0), (-1, -1), 0.6, c["line"]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                              ("LEFTPADDING", (0, 0), (-1, -1), 10), ("ROUNDEDCORNERS", [8, 8, 8, 8])]))
    story += [P("TÓM TẮT NHANH", s_eyebrow), Spacer(1, 2 * mm), P("Những điều cần nắm trước khi đọc chi tiết.", s_h2),
              Spacer(1, 6 * mm), grid, Spacer(1, 7 * mm)]
    opened = [s for s in SECTIONS if s["id"][0] in "BC" and any(q["code"] in applicable for q in QUESTIONS if q["section"] == s["id"])]
    if opened:
        story += [P("NHÁNH ĐÃ MỞ THEO CÂU TRẢ LỜI", s_kpi_l), Spacer(1, 2 * mm)]
        chips = [chip(f"{s['id']} · {s['title']}", c["soft"], c["ink"]) for s in opened]
        rows = [chips[i:i + 3] for i in range(0, len(chips), 3)]
        rows[-1] += [""] * (3 - len(rows[-1]))
        ct = Table(rows, colWidths=[(W - 2 * margin) / 3] * 3, hAlign="LEFT")
        ct.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        story += [ct, Spacer(1, 6 * mm)]
    sec_rows = [s for s in validation.get("sections", []) if s.get("applicable") and not (client and s["id"] == "E")]
    if sec_rows:
        titles = {s["id"]: s for s in SECTIONS}
        th = style("pth", fontName="Body-Bold", fontSize=7.5, leading=10, textColor=c["muted"])
        data = [[P(x, th) for x in ("PHẦN", "MỤC", "ĐÃ TRẢ LỜI", "ĐÃ XÁC NHẬN", "")]]
        for srow in sec_rows:
            meta = titles.get(srow["id"], {"part": "", "title": srow["id"]})
            ratio = srow["answered"] / srow["total"] if srow["total"] else 0
            mini = Bar(ratio, width=34 * mm, height=4)
            data.append([P(meta["part"], s_small), P(meta["title"], s_value), P(f"{srow['answered']}/{srow['total']}", s_value),
                         P(f"{srow['confirmed']}/{srow['total']}", s_value), mini])
        pt = Table(data, colWidths=[22 * mm, inner_w0 - 22 * mm - 26 * mm - 28 * mm - 38 * mm, 26 * mm, 28 * mm, 38 * mm], repeatRows=1)
        pt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, c["line"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story += [P("TIẾN ĐỘ TỪNG PHẦN", s_kpi_l), Spacer(1, 2 * mm), pt, Spacer(1, 6 * mm)]
    issues = validation.get("blockers", []) if not client else [b for b in validation.get("blockers", []) if b["code"] in {"ANSWER_REQUIRED", "NEEDS_CONSULTATION", "ANSWER_UNCLEAR"} and CATALOG.get(b["question_code"], {}).get("audience") != "internal"]
    if issues:
        story += [P("CÒN THIẾU" if client else "VIỆC CÒN MỞ", s_kpi_l), Spacer(1, 2 * mm)]
        rows = [[chip(b["question_code"], c["primary"]), P(b["message"], s_value)] for b in issues[:14]]
        it = Table(rows, colWidths=[18 * mm, W - 2 * margin - 18 * mm], hAlign="LEFT")
        it.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story += [it]
        if len(issues) > 14:
            story += [P(f"… và {len(issues) - 14} mục khác, xem cuối tài liệu.", s_small)]

    # ---------------- Các phần
    inner_w = W - 2 * margin

    cell_w = inner_w - 20  # thẻ có lề trong 10pt mỗi bên

    def question_block(code):
        q = CATALOG[code]
        a = answers.get(code)
        status = a["status"] if a else "UNANSWERED"
        values = answer_rows(code, a["value"]) if a and code != "D1" else []
        compact = values[0][1] if len(values) == 1 and not values[0][0] else None
        middle = [P(q["label"], s_q)] + ([Spacer(1, 3), P(compact, s_answer)] if compact else [])
        head = Table([[chip(code, c["primary"]), middle,
                       chip(STATUS_TEXT.get(status, status), status_color.get(status, c["line"]),
                            c["primary_ink"] if status in status_color else c["muted"])]],
                     colWidths=[20 * mm, cell_w - 20 * mm - 32 * mm, 32 * mm])
        head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                                  ("LEFTPADDING", (1, 0), (1, 0), 6)]))
        rows = [[head, ""]]
        if code == "D1" and a and isinstance(a["value"], dict) and isinstance(a["value"].get("rows"), list) and a["value"]["rows"]:
            field = q["fields"][0]
            th = style("th", fontName="Body-Bold", fontSize=8, leading=10, textColor=c["muted"])
            data = [[P(x, th) for x in ("CẢNH / THỜI GIAN", "ĐỐI TƯỢNG", "CHI TIẾT", "YÊU CẦU", "GIÁ TRỊ", "GHI CHÚ")]]
            for r in a["value"]["rows"]:
                if not isinstance(r, dict):
                    continue
                data.append([P(scope_text(r), s_value), P(_label(field["objects"], r.get("object")), s_value),
                             P(r.get("detail") or "", s_value), P(_label(field["actions"], r.get("action")), s_value),
                             P(r.get("value") or "", s_value), P(r.get("note") or "", s_small)])
            st = Table(data, colWidths=[w * cell_w for w in (0.16, 0.14, 0.2, 0.15, 0.16, 0.19)], repeatRows=1)
            st.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), c["soft"]), ("LINEBELOW", (0, 0), (-1, -1), 0.4, c["line"]),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
            rows.append([st, ""])
        elif not compact:
            if not values:
                rows.append([P("Chưa trả lời" if not a or status != "NEEDS_CONSULTATION" else "Khách cần tư vấn câu này.", s_empty), ""])
            for label, text in values:
                rows.append([P(label or "Trả lời", s_label), P(text, s_value)])
        t = Table(rows, colWidths=[42 * mm, inner_w - 42 * mm])
        cmds = [("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, -1), c["surface"]), ("BOX", (0, 0), (-1, -1), 0.6, c["line"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("TOPPADDING", (0, 1), (-1, -1), 2), ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("ROUNDEDCORNERS", [8, 8, 8, 8])]
        if len(rows) > 1 and rows[1][1] == "":
            cmds += [("SPAN", (0, i), (-1, i)) for i in range(1, len(rows)) if rows[i][1] == ""]
        if status == "CONFIRMED":
            cmds.append(("LINEBEFORE", (0, 0), (0, -1), 2.4, c["good"]))
        t.setStyle(TableStyle(cmds))
        return [t, Spacer(1, 3.2 * mm)]

    class ChapterBand(Flowable):
        def __init__(self, number, eyebrow, title, subtitle, internal=False):
            super().__init__()
            self.number, self.internal = number, internal
            self.parts = [P(eyebrow, style("ce", fontName="Body-Bold", fontSize=8, leading=10, textColor=c["soft"])),
                          P(title, style("ct", fontName="Display", fontSize=23, leading=27, textColor=c["paper"])),
                          P(subtitle, style("cs", fontSize=10, leading=14, textColor=c["line"]))]
            self.width, self.height = inner_w, 34 * mm

        def wrap(self, *_):
            return self.width, self.height

        def draw(self):
            cv = self.canv
            cv.saveState()
            path = cv.beginPath()
            path.roundRect(0, 0, self.width, self.height, 12)
            cv.clipPath(path, stroke=0, fill=0)
            cv.setFillColor(c["ink"])
            cv.rect(0, 0, self.width, self.height, stroke=0, fill=1)
            glow(cv, self.width - 10, self.height, 70 * mm, c["paper"] if self.internal else c["primary"], 0.8)
            glow(cv, 0, 0, 45 * mm, c["accent"], 0.55)
            text = cv.beginText()
            text.setTextRenderMode(1)
            cv.setStrokeColor(c["paper"])
            cv.setStrokeAlpha(0.28)
            cv.setLineWidth(0.9)
            text.setFont("Display", 78)
            text.setTextOrigin(self.width - 50 * mm, 6 * mm)
            text.textOut(self.number)
            cv.drawText(text)
            cv.restoreState()
            y = self.height - 8 * mm
            widths = [self.width * 0.7] * 3
            for part, w in zip(self.parts, widths):
                _, h = part.wrap(w, self.height)
                y -= h
                part.drawOn(cv, 9 * mm, y)
                y -= 2.5

    chapter_no = 0
    last_part = None
    for section in SECTIONS:
        if client and section["id"] == "E":
            continue
        required = set(validation.get("required_codes", []))
        codes = [q["code"] for q in QUESTIONS if q["section"] == section["id"]
                 and (q["code"] in answers and answers[q["code"]].get("applicable") is not False
                      or q["code"] in required)]
        if not codes:
            continue
        if last_part is None:
            story += [PageBreak()]
        last_part = section["part"]
        chapter_no += 1
        eyebrow = f"{section['part'].upper()}{' · ' + section['id'] if section['id'][0] in 'BC' else ''}" + (" · NỘI BỘ – KHÔNG GỬI KHÁCH" if section["id"] == "E" else "")
        header = [ChapterBand(f"{chapter_no:02d}", eyebrow, section["title"], section["subtitle"], internal=section["id"] == "E")]
        blocks = question_block(codes[0])
        story += [CondPageBreak(75 * mm), Spacer(1, 3 * mm), KeepTogether(header + [Spacer(1, 4 * mm)] + blocks)]
        for code in codes[1:]:
            story += [KeepTogether(question_block(code))]
        story += [Spacer(1, 5 * mm)]

    # ---------------- Việc còn mở và duyệt
    if not client:
        story += [CondPageBreak(110 * mm), Spacer(1, 6 * mm), P("KIỂM TRA", s_eyebrow), Spacer(1, 1.5 * mm), P("Việc còn mở và quyết định", s_h2), Spacer(1, 5 * mm)]
        for title, items, color in (("Chặn việc gửi duyệt", validation.get("blockers", []), c["danger"]),
                                    ("Cần làm rõ", validation.get("clarifications", []), c["accent"])):
            story += [P(f"{title.upper()} · {len(items)}", s_kpi_l), Spacer(1, 2 * mm)]
            if not items:
                story += [P("Không có.", s_empty), Spacer(1, 4 * mm)]
                continue
            rows = [[chip(i["question_code"], color), P(i["message"], s_value)] for i in items]
            t = Table(rows, colWidths=[18 * mm, inner_w - 18 * mm], hAlign="LEFT")
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story += [t, Spacer(1, 5 * mm)]
        dec = decision or {"decision": "PENDING"}
        rows = [[P("Quyết định", s_label), P({"APPROVED": "Đã duyệt", "CHANGES_REQUESTED": "Yêu cầu chỉnh sửa", "REJECTED": "Từ chối"}.get(dec.get("decision"), "Chưa có quyết định"), s_value)],
                [P("Snapshot", s_label), P((snapshot or {}).get("hash") or "Chưa gửi duyệt", s_small)],
                [P("Ghi chú", s_label), P(dec.get("notes") or "—", s_value)]]
        t = Table(rows, colWidths=[42 * mm, inner_w - 42 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c["surface"]), ("BOX", (0, 0), (-1, -1), 0.6, c["line"]),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ROUNDEDCORNERS", [8, 8, 8, 8])]))
        story += [P("DUYỆT", s_kpi_l), Spacer(1, 2 * mm), t]
    legacy = [a for a in payload["answers"] if a["question_code"] not in CATALOG]
    if legacy and not client:
        story += [Spacer(1, 6 * mm), P("CÂU TRẢ LỜI CỦA BỘ CÂU HỎI CŨ (CHỈ LƯU LỊCH SỬ)", s_kpi_l)]
        story += [P(f"{a['question_code']}: {answer_text(a['question_code'], a['value'])}", s_small) for a in legacy]

    buf = io.BytesIO()
    doc.filename = buf
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def export_package(payload, fmt, decision=None, snapshot=None, source_dir=None):
    if fmt == "json":
        # Signed payload/hash stay frozen. Envelope validity is deliberately current,
        # so an old approved snapshot cannot be mistaken for the active contract.
        return canonical({"payload": payload, "snapshot": snapshot, "approval": decision, "delivery_matrix": delivery_matrix(payload["answers"])}).encode(), "application/json", "json"
    if fmt == "xlsx":
        from .xlsx_export import xlsx_zip
        return xlsx_zip(payload, _state(decision, snapshot)[0], decision, source_dir), "application/zip", "zip"
    files, sheet = package_files(payload, decision, snapshot)
    if fmt == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr("01_TIEP_NHAN_VA_FOLDER_THONG_TIN/" + name, content.encode("utf-8"))
        return buf.getvalue(), "application/zip", "zip"
    if fmt == "docx":
        return _docx(payload, decision, snapshot, files), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
    if fmt in {"pdf", "client_pdf"}:
        return _pdf(payload, decision, snapshot, files, client=fmt == "client_pdf"), "application/pdf", "pdf"
    raise ValueError("Định dạng xuất không hỗ trợ.")
