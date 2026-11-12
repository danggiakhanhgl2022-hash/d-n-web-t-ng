"""Bộ 5 file Excel từ một phiếu tiếp nhận. Mỗi file một mục đích, bố cục dễ nhìn, in được."""
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import xlsxwriter

from .questionnaire import (CATALOG, QUESTIONS, SECTIONS, answer_text, answer_rows, delivery_matrix, scope_text, _label)

HERE = Path(__file__).resolve().parent
BRAND = json.loads((HERE / "brand.json").read_text(encoding="utf-8"))
STATUS_TEXT = {"CONFIRMED": "Đã xác nhận", "ANSWERED_UNCONFIRMED": "Chờ xác nhận", "PROPOSED_FROM_SOURCE": "Gợi ý từ tài liệu",
               "NEEDS_CONSULTATION": "Cần tư vấn", "CONFLICTED": "Có mâu thuẫn", "UNKNOWN": "Chưa xác định",
               "NOT_APPLICABLE": "Không áp dụng", "UNANSWERED": "Chưa trả lời"}
STATUS_COLOR = {"CONFIRMED": "#DFF3E4", "ANSWERED_UNCONFIRMED": "#FFF4D6", "NEEDS_CONSULTATION": "#FFE3D3",
                "CONFLICTED": "#FAD4D4", "UNKNOWN": "#EDEDED", "UNANSWERED": "#EDEDED", "PROPOSED_FROM_SOURCE": "#E3EEF7"}
KIND_OF = {"video": "Video", "image": "Ảnh", "audio": "Âm thanh / ghi âm"}
SECTION_TITLE = {s["id"]: s.get("title", s["id"]) for s in SECTIONS}
FONT = "Calibri"


def _kind(mime, name):
    mime = (mime or "").lower()
    for k in KIND_OF:
        if mime.startswith(k + "/"):
            return KIND_OF[k]
    if name.lower().endswith((".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".ppt", ".pptx")):
        return "Tài liệu"
    return "Khác"


def _size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _date(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(text or "")


class Book:
    """Một workbook với bộ định dạng chung theo màu thương hiệu."""

    def __init__(self, title):
        self.buf = io.BytesIO()
        self.wb = xlsxwriter.Workbook(self.buf, {"in_memory": True})
        self.wb.set_properties({"title": title, "author": BRAND.get("studio_name", "")})
        primary = BRAND["colors"]["primary"] if "colors" in BRAND else "#E4572E"
        ink = "#17181C"
        base = {"font_name": FONT, "font_size": 11, "valign": "top", "text_wrap": True}
        f = self.wb.add_format
        self.f = {
            "title": f({**base, "font_size": 20, "bold": True, "font_color": "#FFFFFF", "bg_color": ink, "valign": "vcenter", "text_wrap": False}),
            "sub": f({**base, "font_color": "#D9D9D9", "bg_color": ink, "valign": "vcenter", "text_wrap": False}),
            "head": f({**base, "bold": True, "font_color": "#FFFFFF", "bg_color": primary, "border": 1, "border_color": "#FFFFFF", "valign": "vcenter"}),
            "band": f({**base, "bold": True, "font_size": 13, "font_color": "#FFFFFF", "bg_color": "#2F6F8F", "valign": "vcenter", "text_wrap": False}),
            "label": f({**base, "bold": True, "bg_color": "#F1EEE8", "border": 1, "border_color": "#D8D2C7"}),
            "cell": f({**base, "border": 1, "border_color": "#D8D2C7"}),
            "alt": f({**base, "border": 1, "border_color": "#D8D2C7", "bg_color": "#FAF8F4"}),
            "center": f({**base, "border": 1, "border_color": "#D8D2C7", "align": "center", "valign": "vcenter"}),
            "num": f({**base, "border": 1, "border_color": "#D8D2C7", "align": "center", "valign": "vcenter", "bold": True, "font_size": 16}),
            "note": f({**base, "italic": True, "font_color": "#6B6B6B"}),
            "wrap_big": f({**base, "border": 1, "border_color": "#D8D2C7", "font_size": 12}),
        }
        self.status_fmt = {k: f({**base, "border": 1, "border_color": "#D8D2C7", "bg_color": v, "align": "center", "valign": "vcenter", "bold": True})
                           for k, v in STATUS_COLOR.items()}
        self.status_default = f({**base, "border": 1, "border_color": "#D8D2C7", "align": "center", "valign": "vcenter"})

    def sheet(self, name, widths, title, subtitle):
        ws = self.wb.add_worksheet(name[:31])
        ws.hide_gridlines(2)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        ws.set_margins(0.4, 0.4, 0.5, 0.5)
        for i, w in enumerate(widths):
            ws.set_column(i, i, w)
        last = len(widths) - 1
        ws.set_row(0, 38)
        ws.set_row(1, 22)
        ws.merge_range(0, 0, 0, last, title, self.f["title"])
        ws.merge_range(1, 0, 1, last, subtitle, self.f["sub"])
        ws.set_footer("&L" + BRAND.get("studio_name", "") + "&C&P / &N&R&D")
        return ws

    def close(self):
        self.wb.close()
        return self.buf.getvalue()


def _head(project, answers):
    by = {a["question_code"]: a for a in answers if not a.get("scope_id") and a.get("applicable", True)}
    return by


def _full(by, code):
    a = by.get(code)
    return answer_text(code, a["value"]) if a and a.get("value") is not None else ""


def _pick(by, code, field=None):
    a = by.get(code)
    if not a or not isinstance(a.get("value"), dict):
        return ""
    rows = answer_rows(code, a["value"])
    if field:
        q = CATALOG.get(code, {})
        label = next((f.get("label", "") for f in q.get("fields", []) if f["id"] == field), None)
        for lab, text in rows:
            if lab == label:
                return text
        return ""
    return " · ".join(t for _, t in rows)


def _subtitle(project, state):
    return f"Đơn: {project['name']}  ·  Khách: {project['customer']}  ·  Bản {project['revision']}  ·  {state}"


def _files_for(payload, paths):
    paths = paths if isinstance(paths, dict) else {}
    return [(s, paths.get(s["id"])) for s in payload["sources"]]


# --------------------------------------------------------------------- 1
def _file1(payload, state, decision):
    project, answers, val = payload["project"], payload["answers"], payload["validation"]
    by = _head(project, answers)
    b = Book("1 · Tổng quan đơn")
    ws = b.sheet("Tổng quan", [26, 34, 26, 34], "TỔNG QUAN ĐƠN", _subtitle(project, state))
    r = 3
    ws.merge_range(r, 0, r, 3, "Thông tin chính", b.f["band"]); r += 1
    pairs = [("Tên đơn", project["name"]), ("Khách hàng", project["customer"]),
             ("Tên dự án / đơn vị", _full(by, "A1")), ("Người trao đổi, liên hệ", _full(by, "A2")),
             ("Loại khách", _pick(by, "P1")), ("Loại video", _pick(by, "P3")),
             ("Video dùng để làm gì", _pick(by, "A3")), ("Người xem video", _full(by, "A4")),
             ("Mốc thời gian", _full(by, "A14")), ("Ngân sách", _pick(by, "A15")),
             ("Phiên bản phiếu", str(project["revision"])), ("Trạng thái duyệt", state)]
    for i in range(0, len(pairs), 2):
        ws.set_row(r, 36)
        ws.write(r, 0, pairs[i][0], b.f["label"]); ws.write(r, 1, pairs[i][1], b.f["cell"])
        if i + 1 < len(pairs):
            ws.write(r, 2, pairs[i + 1][0], b.f["label"]); ws.write(r, 3, pairs[i + 1][1], b.f["cell"])
        r += 1
    r += 1
    ws.merge_range(r, 0, r, 3, "Mức đầy đủ của phiếu", b.f["band"]); r += 1
    required = val.get("required_codes", [])
    filled = {a["question_code"] for a in answers if not a.get("scope_id") and a.get("applicable", True)
              and a["status"] not in {"UNANSWERED", "UNKNOWN", "NEEDS_CONSULTATION"}
              and not (isinstance(a.get("value"), dict) and not any(v not in (None, "", [], {}) for v in a["value"].values()))}
    done = sum(1 for c in required if c in filled)
    total = len(required)
    pct = (done / total) if total else 0
    pct_fmt = b.wb.add_format({"num_format": "0%", "font_name": FONT, "font_size": 16, "bold": True, "align": "center", "valign": "vcenter", "border": 1, "border_color": "#D8D2C7"})
    ws.write(r, 0, "Câu bắt buộc khách đã trả lời", b.f["label"]); ws.write(r, 1, f"{done} / {total}", b.f["num"])
    ws.write(r, 2, "Tỷ lệ đã trả lời", b.f["label"]); ws.write_number(r, 3, pct, pct_fmt)
    ws.set_row(r, 32); r += 1
    missing = sum(1 for x in val["blockers"] if x.get("code") == "ANSWER_REQUIRED")
    waiting = sum(1 for x in val["blockers"] if x.get("code") == "NEEDS_CONFIRMATION")
    other = len(val["blockers"]) - missing - waiting
    ws.write(r, 0, "Còn thiếu câu trả lời", b.f["label"]); ws.write(r, 1, missing, b.f["num"])
    ws.write(r, 2, "Chờ bạn xác nhận", b.f["label"]); ws.write(r, 3, waiting, b.f["num"])
    ws.set_row(r, 32); r += 1
    ws.write(r, 0, "Mâu thuẫn / cần xử lý", b.f["label"]); ws.write(r, 1, other, b.f["num"])
    ws.write(r, 2, "Cần làm rõ thêm", b.f["label"]); ws.write(r, 3, len(val.get("clarifications", [])), b.f["num"])
    ws.set_row(r, 32); r += 2
    ws.merge_range(r, 0, r, 3, "Tiến độ theo phần", b.f["band"]); r += 1
    for c, h in enumerate(["Phần", "Tên phần", "Đã trả lời / Cần", "Vướng"]):
        ws.write(r, c, h, b.f["head"])
    r += 1
    for i, sec in enumerate(val.get("sections", [])):
        if isinstance(sec, dict) and sec.get("applicable") and sec.get("id") != "E":
            fm = b.f["cell"] if i % 2 == 0 else b.f["alt"]
            ws.write(r, 0, sec["id"], fm)
            ws.write(r, 1, SECTION_TITLE.get(sec["id"], ""), fm)
            ws.write(r, 2, f"{sec.get('answered', 0)} / {sec.get('required', 0)}", fm)
            ws.write(r, 3, sec.get("issues", 0), b.f["center"])
            r += 1
    m = payload.get("delivery_matrix") or delivery_matrix(answers)
    r += 1
    ws.merge_range(r, 0, r, 3, "Số lượng bàn giao", b.f["band"]); r += 1
    for lab, v in (("Số video", m.get("total_base")), ("Tổng số file", m.get("total_files")), ("Cách tính", m.get("variant_policy"))):
        ws.write(r, 0, lab, b.f["label"]); ws.merge_range(r, 1, r, 3, str(v) if v is not None else "", b.f["cell"]); r += 1
    ws.freeze_panes(2, 0)
    return b.close()


# --------------------------------------------------------------------- 2
def _file2(payload, state, decision):
    project, answers = payload["project"], payload["answers"]
    by_code = {q["code"]: q for q in payload.get("questionnaire_definition", QUESTIONS) if isinstance(q, dict) and "code" in q}
    b = Book("2 · Yêu cầu chi tiết")
    ws = b.sheet("Yêu cầu", [8, 46, 62, 18, 28], "YÊU CẦU CHI TIẾT", _subtitle(project, state))
    ws.set_row(3, 24)
    for c, h in enumerate(["Mã", "Câu hỏi", "Khách trả lời", "Trạng thái", "Ghi chú của bạn"]):
        ws.write(3, c, h, b.f["head"])
    ws.autofilter(3, 0, 3, 4)
    ws.freeze_panes(4, 0)
    order = {s["id"]: i for i, s in enumerate(SECTIONS)}
    qorder = {q["code"]: i for i, q in enumerate(QUESTIONS)}
    rows = [a for a in answers if a.get("applicable", True) and a["question_code"] != "D1"]
    rows.sort(key=lambda a: (order.get((CATALOG.get(a["question_code"]) or {}).get("section"), 99), qorder.get(a["question_code"], 999)))
    r, current = 4, None
    for a in rows:
        q = CATALOG.get(a["question_code"]) or by_code.get(a["question_code"]) or {"label": "Câu hỏi của bộ cũ"}
        sec = q.get("section")
        if sec == "E":
            continue
        if sec != current:
            ws.merge_range(r, 0, r, 4, SECTION_TITLE.get(sec, sec or ""), b.f["band"]); ws.set_row(r, 24); r += 1; current = sec
        text = answer_text(a["question_code"], a["value"]) or "—"
        ws.set_row(r, max(30, min(220, 16 * (1 + text.count("\n") + len(text) // 70))))
        ws.write(r, 0, a["question_code"], b.f["center"])
        ws.write(r, 1, q["label"], b.f["cell"])
        ws.write(r, 2, text, b.f["wrap_big"])
        ws.write(r, 3, STATUS_TEXT.get(a["status"], a["status"]), b.status_fmt.get(a["status"], b.status_default))
        ws.write(r, 4, "", b.f["cell"])
        r += 1
    return b.close()


# --------------------------------------------------------------------- 3
def _file3(payload, state, decision):
    project, answers = payload["project"], payload["answers"]
    b = Book("3 · Cảnh và bàn giao")
    ws = b.sheet("Bàn giao", [30, 26, 26, 26, 26], "SỐ LƯỢNG VÀ BÀN GIAO", _subtitle(project, state))
    m = payload.get("delivery_matrix") or delivery_matrix(answers)
    r = 3
    ws.merge_range(r, 0, r, 4, "Ma trận bàn giao", b.f["band"]); r += 1
    items = m.get("items") or []
    for c, h in enumerate(["Hạng mục", "Số lượng", "Khung hình", "Thời lượng", "Ngôn ngữ"]):
        ws.write(r, c, h, b.f["head"])
    r += 1
    if not items:
        ws.merge_range(r, 0, r, 4, "Chưa đủ thông tin để tính số lượng.", b.f["cell"]); r += 1
    for it in items:
        ws.write(r, 0, it["id"], b.f["cell"]); ws.write(r, 1, it["quantity"], b.f["center"])
        ws.write(r, 2, ", ".join(it.get("aspect_ratios") or []), b.f["cell"]); ws.write(r, 3, it.get("duration") or "", b.f["cell"])
        ws.write(r, 4, ", ".join(it.get("languages") or []), b.f["cell"]); r += 1
    r += 1
    for lab, v in (("Tổng số file", m.get("total_files")), ("Số video tính tiền", m.get("total_counted")), ("Cách tính", m.get("variant_policy")), ("Quy tắc", m.get("counting_rule"))):
        ws.write(r, 0, lab, b.f["label"]); ws.merge_range(r, 1, r, 4, str(v) if v is not None else "", b.f["cell"]); r += 1
    d1 = next((a for a in answers if a["question_code"] == "D1" and a.get("applicable", True)), None)
    ws2 = b.sheet("Yêu cầu theo cảnh", [6, 20, 18, 42, 18, 34, 30], "YÊU CẦU THEO CẢNH", _subtitle(project, state))
    for c, h in enumerate(["#", "Ở đâu", "Đối tượng", "Chi tiết", "Yêu cầu", "Đổi thành", "Ghi chú"]):
        ws2.write(3, c, h, b.f["head"])
    ws2.freeze_panes(4, 0)
    field = next((f for f in CATALOG["D1"]["fields"] if f["id"] == "rows"), None)
    rows = (d1["value"].get("rows") if d1 and isinstance(d1.get("value"), dict) else None) or []
    r = 4
    if not rows:
        ws2.merge_range(r, 0, r, 6, "Khách chưa ghi yêu cầu theo cảnh.", b.f["cell"])
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        fm = b.f["cell"] if i % 2 else b.f["alt"]
        ws2.write(r, 0, i, b.f["center"]); ws2.write(r, 1, scope_text(row), fm)
        ws2.write(r, 2, _label(field["objects"], row.get("object")) if field else row.get("object", ""), fm)
        ws2.write(r, 3, row.get("detail", ""), fm)
        ws2.write(r, 4, _label(field["actions"], row.get("action")) if field else row.get("action", ""), fm)
        ws2.write(r, 5, row.get("value") or "", fm); ws2.write(r, 6, row.get("note") or "", fm)
        r += 1
    return b.close()


# --------------------------------------------------------------------- 4
def _file4(payload, state, decision, source_dir):
    project = payload["project"]
    b = Book("4 · Tư liệu khách gửi")
    ws = b.sheet("Tư liệu", [30, 32, 16, 12, 16, 40, 40, 14, 30], "TƯ LIỆU KHÁCH GỬI", _subtitle(project, state))
    for c, h in enumerate(["Xem nhanh", "Tên tệp", "Loại", "Dung lượng", "Ngày nhận", "Khách ghi chú", "Gắn với câu", "Nguồn", "Ghi chú của bạn"]):
        ws.write(3, c, h, b.f["head"])
    ws.autofilter(3, 0, 3, 8)
    ws.freeze_panes(4, 0)
    r = 4
    files = _files_for(payload, source_dir)
    if not files:
        ws.merge_range(r, 0, r, 8, "Khách chưa gửi tệp nào.", b.f["cell"])
    for s, path in files:
        kind = _kind(s.get("mime_type"), s["filename"])
        ws.set_row(r, 96 if kind == "Ảnh" else 44)
        ws.write(r, 0, "", b.f["cell"])
        if kind == "Ảnh" and path:
            try:
                from PIL import Image
                im = Image.open(path)
                im.thumbnail((190, 120))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                bio = io.BytesIO(); im.save(bio, "JPEG", quality=80)
                ws.insert_image(r, 0, s["filename"], {"image_data": bio, "x_offset": 4, "y_offset": 4, "object_position": 1})
            except Exception:
                ws.write(r, 0, "(không tạo được ảnh xem trước)", b.f["cell"])
        ws.write(r, 1, s["filename"], b.f["cell"]); ws.write(r, 2, kind, b.f["center"])
        ws.write(r, 3, _size(s.get("size")), b.f["center"]); ws.write(r, 4, _date(s.get("created_at")), b.f["center"])
        text = (s.get("note") or "").strip() or (s.get("extracted_text") or "").strip()
        ws.write(r, 5, (text[:600] + "…") if len(text) > 600 else (text or "—"), b.f["cell"])
        code = s.get("question_code")
        qlabel = (CATALOG.get(code) or {}).get("label", "") if code else ""
        ws.write(r, 6, f"{code} · {qlabel}" if code else "Chung cho cả đơn", b.f["cell"])
        ws.write(r, 7, "Khách gửi qua link" if s.get("via") == "CLIENT_LINK" else "Bạn tải lên", b.f["center"])
        ws.write(r, 8, "", b.f["cell"])
        r += 1
    r += 1
    ws.merge_range(r, 0, r, 8, "Ảnh xem nhanh chỉ để nhận diện. Tệp gốc nằm trong gói .zip của đơn hoặc thư mục tư liệu của ứng dụng.", b.f["note"])
    return b.close()


# --------------------------------------------------------------------- 5
def _file5(payload, state, decision):
    project, answers, val = payload["project"], payload["answers"], payload["validation"]
    b = Book("5 · Việc cần hỏi lại")
    ws = b.sheet("Cần hỏi lại", [6, 10, 62, 16, 16, 18, 34], "VIỆC CẦN HỎI LẠI VÀ LÀM", _subtitle(project, state))
    for c, h in enumerate(["#", "Mã câu", "Việc cần làm / điều chưa rõ", "Mức", "Ai làm", "Tình trạng", "Ghi chú"]):
        ws.write(3, c, h, b.f["head"])
    ws.freeze_panes(4, 0)
    ws.autofilter(3, 0, 3, 6)
    items = [(x, "Phải xong trước khi báo giá") for x in val["blockers"] if x.get("code") != "NEEDS_CONFIRMATION"] + [(x, "Nên hỏi thêm") for x in val.get("clarifications", [])]
    for a in answers:
        if a["status"] in {"NEEDS_CONSULTATION", "CONFLICTED"} and a.get("applicable", True):
            items.append(({"question_code": a["question_code"], "message": "Khách chọn “cần tư vấn”: gọi hỏi lại.", "owner_role": "ACCOUNT"}, "Cần tư vấn"))
    r = 4
    if not items:
        ws.merge_range(r, 0, r, 6, "Không còn việc nào cần hỏi lại.", b.f["cell"])
    state_fmt = b.wb.add_format({"font_name": FONT, "border": 1, "border_color": "#D8D2C7", "align": "center", "valign": "vcenter"})
    for i, (x, level) in enumerate(items, 1):
        ws.set_row(r, 34)
        ws.write(r, 0, i, b.f["center"]); ws.write(r, 1, x["question_code"], b.f["center"])
        ws.write(r, 2, x["message"], b.f["cell"]); ws.write(r, 3, level, b.f["cell"])
        ws.write(r, 4, "Tôi" if x.get("owner_role") in (None, "PM") else "Hỏi khách", b.f["center"])
        ws.write(r, 5, "Chưa làm", state_fmt); ws.write(r, 6, "", b.f["cell"])
        r += 1
    last = max(r, 5) - 1
    ws.data_validation(4, 5, max(last, 4) + 40, 5, {"validate": "list", "source": ["Chưa làm", "Đang hỏi khách", "Chờ khách trả lời", "Xong"]})
    r += 2
    ws.merge_range(r, 0, r, 6, "Phản hồi đã ghi", b.f["band"]); r += 1
    fb = payload.get("feedback") or []
    if not fb:
        ws.merge_range(r, 0, r, 6, "Chưa có phản hồi.", b.f["cell"])
    for f in fb:
        ws.write(r, 0, "", b.f["cell"]); ws.write(r, 1, "", b.f["cell"])
        ws.merge_range(r, 2, r, 6, f"{_date(f.get('created_at'))}: {f.get('message', '')}", b.f["cell"]); r += 1
    return b.close()


NAMES = ["01_TONG_QUAN_DON.xlsx", "02_YEU_CAU_CHI_TIET.xlsx", "03_CANH_VA_BAN_GIAO.xlsx",
         "04_TU_LIEU_KHACH_GUI.xlsx", "05_VIEC_CAN_HOI_LAI.xlsx"]


def xlsx_files(payload, state, decision=None, source_dir=None):
    return {NAMES[0]: _file1(payload, state, decision), NAMES[1]: _file2(payload, state, decision),
            NAMES[2]: _file3(payload, state, decision), NAMES[3]: _file4(payload, state, decision, source_dir),
            NAMES[4]: _file5(payload, state, decision)}


def xlsx_zip(payload, state, decision=None, source_dir=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in xlsx_files(payload, state, decision, source_dir).items():
            z.writestr(name, data)
    return buf.getvalue()
