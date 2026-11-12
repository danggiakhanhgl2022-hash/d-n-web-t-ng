"""Bộ câu hỏi tiếp nhận v3: rẽ nhánh theo kiểu khách và loại video.

Định nghĩa câu hỏi nằm trong questions.json. Mỗi câu trả lời là một object
{<mã trường>: giá trị}. Trường "Khác" lưu ở "<mã trường>__other".
"Không áp dụng" lưu là {"_na": true} và chỉ hợp lệ với câu có allow_na.
"""
import json
import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path

_DEFINITION = json.loads(Path(__file__).with_name("questions.json").read_text(encoding="utf-8"))
TEMPLATE_VERSION = _DEFINITION["template_version"]
SECTIONS = _DEFINITION["sections"]
QUESTIONS = _DEFINITION["questions"]
CATALOG = {q["code"]: q for q in QUESTIONS}
STAR_CODES = [q["code"] for q in QUESTIONS if q.get("star")]
# Giữ tên cũ cho các module khác: CORE = các câu luôn hỏi mọi khách (Phần 0 và A).
CORE_CODES = [q["code"] for q in QUESTIONS if q["group"] in {"P", "A"}]
STATES = {"UNANSWERED", "PROPOSED_FROM_SOURCE", "ANSWERED_UNCONFIRMED", "CONFIRMED", "UNKNOWN", "NEEDS_CONSULTATION",
          "NOT_APPLICABLE", "CONFLICTED", "WAIVED_WITH_REASON"}
ALWAYS_GROUPS = {"P", "A", "D", "E"}
CONFLICTING_ACTIONS = [{"ON", "OFF"}, {"KEEP", "CHANGE"}]
POLICY_VERSION = "stage01-policy-v3"


def canonical(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    encoded.encode("utf-8")  # Reject lone surrogates before persistence/response serialization.
    return encoded


def is_number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _option_ids(field, key="options"):
    return {opt["id"] for opt in field.get(key, [])}


def _label(options, ident):
    return next((opt["label"] for opt in options if opt["id"] == ident), ident)


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def is_na(question, value):
    return bool(question.get("allow_na")) and isinstance(value, dict) and value.get("_na") is True


def _empty(field, raw):
    kind = field["type"]
    if raw is None:
        return True
    if kind in {"text", "textarea", "date"}:
        return not nonempty(raw)
    if kind == "multi":
        return not isinstance(raw, list) or not raw
    if kind in {"matrix_multi", "matrix_single"}:
        return not isinstance(raw, dict) or not any(raw.get(r["id"]) for r in field["rows"])
    if kind == "scene_table":
        return not isinstance(raw, list) or not raw
    if kind == "single":
        return not nonempty(raw)
    return False


def _field_errors(field, value):
    """Trả về lỗi của một trường; value là cả object câu trả lời."""
    label = field.get("label") or "Câu trả lời"
    raw = value.get(field["id"])
    kind = field["type"]
    if _empty(field, raw):
        return [f"{label}: chưa điền."] if field.get("required", True) else []
    errors = []
    if kind in {"text", "textarea"}:
        if not isinstance(raw, str):
            return [f"{label}: cần nội dung chữ."]
        if len(raw) > field.get("max_length", 2000):
            errors.append(f"{label}: dài quá {field.get('max_length', 2000)} ký tự.")
    elif kind == "single":
        if not isinstance(raw, str):
            return [f"{label}: lựa chọn không hợp lệ."]
        if raw == "OTHER" and field.get("other"):
            if not nonempty(value.get(field["id"] + "__other")):
                errors.append(f"{label}: chọn “Khác” thì cần ghi rõ.")
        elif raw not in _option_ids(field):
            errors.append(f"{label}: lựa chọn không có trong danh sách.")
    elif kind == "multi":
        if not isinstance(raw, list) or any(not isinstance(x, str) for x in raw):
            return [f"{label}: danh sách lựa chọn không hợp lệ."]
        allowed = _option_ids(field) | ({"OTHER"} if field.get("other") else set())
        bad = [x for x in raw if x not in allowed]
        if bad:
            errors.append(f"{label}: có lựa chọn không có trong danh sách.")
        if len(set(raw)) != len(raw):
            errors.append(f"{label}: có lựa chọn bị lặp.")
        if field.get("max_items") and len(raw) > field["max_items"]:
            errors.append(f"{label}: chọn tối đa {field['max_items']} mục.")
        exclusive = set(field.get("exclusive", []))
        if exclusive & set(raw) and len(raw) > 1:
            names = ", ".join(_label(field["options"], x) for x in exclusive & set(raw))
            errors.append(f"{label}: “{names}” không đi cùng lựa chọn khác.")
        if "OTHER" in raw and not nonempty(value.get(field["id"] + "__other")):
            errors.append(f"{label}: chọn “Khác” thì cần ghi rõ.")
    elif kind == "number":
        if not is_number(raw):
            return [f"{label}: cần một con số."]
        if field.get("integer") and int(raw) != raw:
            errors.append(f"{label}: cần số nguyên.")
        if raw < field.get("min", 0) or raw > field.get("max", 10 ** 12):
            errors.append(f"{label}: cần trong khoảng {field.get('min', 0)}–{field.get('max')}.")
    elif kind == "date":
        if not parse_date(raw):
            errors.append(f"{label}: cần ngày hợp lệ (YYYY-MM-DD).")
    elif kind == "matrix_single":
        if not isinstance(raw, dict):
            return [f"{label}: dữ liệu bảng không hợp lệ."]
        cols = _option_ids(field, "cols")
        rows = {r["id"]: r["label"] for r in field["rows"]}
        for row_id, row_label in rows.items():
            cell = raw.get(row_id)
            if cell is None:
                if field.get("required", True):
                    errors.append(f"{label}: “{row_label}” chưa chọn.")
            elif not isinstance(cell, str) or cell not in cols:
                errors.append(f"{label}: “{row_label}” có lựa chọn không hợp lệ.")
        if set(raw) - set(rows):
            errors.append(f"{label}: có dòng không có trong bảng.")
    elif kind == "matrix_multi":
        if not isinstance(raw, dict):
            return [f"{label}: dữ liệu bảng không hợp lệ."]
        cols = _option_ids(field, "cols")
        exclusive = set(field.get("exclusive", []))
        rows = {r["id"]: r["label"] for r in field["rows"]}
        for row_id, row_label in rows.items():
            cell = raw.get(row_id)
            if cell is None or cell == []:
                if field.get("required", True):
                    errors.append(f"{label}: “{row_label}” chưa chọn (chọn “Không dùng” nếu không cần).")
                continue
            if not isinstance(cell, list) or any(not isinstance(x, str) or x not in cols for x in cell):
                errors.append(f"{label}: “{row_label}” có lựa chọn không hợp lệ.")
            elif exclusive & set(cell) and len(cell) > 1:
                errors.append(f"{label}: “{row_label}” không thể vừa “Không dùng” vừa chọn ngôn ngữ.")
        if set(raw) - set(rows):
            errors.append(f"{label}: có dòng không có trong bảng.")
    elif kind == "scene_table":
        errors.extend(scene_errors(field, raw))
    return errors


def _scope_key(row):
    kind = row.get("scope")
    if kind == "SCENE":
        return ("SCENE", row.get("a"))
    if kind == "FROM":
        return ("FROM", row.get("a"))
    if kind == "TIME":
        return ("TIME", row.get("a"), row.get("b"))
    return ("ALL",)


def _norm(text):
    return re.sub(r"\s+", " ", text.strip().lower()) if isinstance(text, str) else ""


def scope_text(row):
    kind = row.get("scope")
    a, b = row.get("a"), row.get("b")
    fmt = lambda x: (str(int(x)) if is_number(x) and int(x) == x else str(x))
    if kind == "SCENE":
        return f"Cảnh {fmt(a)}"
    if kind == "FROM":
        return f"Từ cảnh {fmt(a)} trở đi"
    if kind == "TIME":
        return f"{fmt(a)}s–{fmt(b)}s"
    return "Toàn video"


def scene_errors(field, rows):
    if not isinstance(rows, list):
        return ["Bảng yêu cầu theo cảnh không hợp lệ."]
    errors = []
    kinds, objects, actions = _option_ids(field, "scope_kinds"), _option_ids(field, "objects"), _option_ids(field, "actions")
    seen = {}
    if len(rows) > 300:
        errors.append("Bảng có quá 300 dòng.")
    for i, row in enumerate(rows, 1):
        tag = f"Dòng {i}"
        if not isinstance(row, dict):
            errors.append(f"{tag}: dữ liệu không hợp lệ.")
            continue
        kind = row.get("scope")
        if not _in(kind, kinds):
            errors.append(f"{tag}: chưa chọn cảnh hoặc thời gian.")
            continue
        a, b = row.get("a"), row.get("b")
        if kind in {"SCENE", "FROM"} and (not is_number(a) or int(a) != a or not 1 <= a <= 999):
            errors.append(f"{tag}: cần số cảnh 1–999.")
        if kind == "TIME":
            if not is_number(a) or not is_number(b) or a < 0 or b <= a or b > 86400:
                errors.append(f"{tag}: cần giây bắt đầu nhỏ hơn giây kết thúc.")
        if not _in(row.get("object"), objects):
            errors.append(f"{tag}: chưa chọn đối tượng.")
        if not nonempty(row.get("detail")):
            errors.append(f"{tag}: cần ghi chi tiết (ví dụ “tiếng mưa”, “áo”).")
        action = row.get("action")
        if not _in(action, actions):
            errors.append(f"{tag}: chưa chọn yêu cầu.")
        elif action == "CHANGE" and not nonempty(row.get("value")):
            errors.append(f"{tag}: “Đổi thành” cần ghi giá trị mong muốn.")
        for key in ("detail", "value", "note"):
            if row.get(key) is not None and not isinstance(row.get(key), str):
                errors.append(f"{tag}: trường {key} cần là chữ.")
        if errors and errors[-1].startswith(tag):
            continue
        key = (_scope_key(row), row.get("object"), _norm(row.get("detail")))
        for j, prev in seen.get(key, []):
            pair = {prev.get("action"), action}
            if any(pair == c for c in CONFLICTING_ACTIONS):
                errors.append(f"Dòng {j} và dòng {i} mâu thuẫn: cùng {scope_text(row)}, cùng “{row.get('detail')}”"
                              f" nhưng một dòng {_label(field['actions'], prev.get('action'))}, một dòng "
                              f"{_label(field['actions'], action)}. Hỏi lại khách.")
            elif action == prev.get("action") == "CHANGE" and _norm(prev.get("value")) != _norm(row.get("value")):
                errors.append(f"Dòng {j} và dòng {i} mâu thuẫn: cùng đổi “{row.get('detail')}” ở {scope_text(row)} "
                              f"nhưng sang hai giá trị khác nhau.")
        seen.setdefault(key, []).append((i, row))
    return errors


def semantic_errors(code, value, today=None):
    """Lỗi của một câu trả lời. today (date) bật kiểm tra ngày đã qua; chỉ dùng khi xác nhận."""
    question = CATALOG.get(code)
    if not question:
        return ["Mã câu hỏi không tồn tại trong phiên bản bộ câu hỏi."]
    if isinstance(value, dict) and value.get("_na") is True:
        return [] if question.get("allow_na") else ["Câu này không có lựa chọn “Không áp dụng”."]
    if not isinstance(value, dict):
        return ["Cần dữ liệu có cấu trúc cho câu hỏi này."]
    errors = []
    known = {f["id"] for f in question["fields"]} | {f["id"] + "__other" for f in question["fields"]}
    if set(value) - known:
        errors.append("Có trường không thuộc câu hỏi.")
    for field in question["fields"]:
        errors.extend(_field_errors(field, value))
    if errors:
        return errors
    # Kiểm tra trong cùng câu.
    if code == "A14":
        preview, final, publish = (parse_date(value.get(k)) for k in ("preview", "final", "publish"))
        if preview and final and preview > final:
            errors.append("Bản xem trước phải đến trước hoặc cùng ngày bản chính thức.")
        if publish and final and publish < final:
            errors.append("Ngày đăng không được trước ngày nhận bản chính thức.")
        if today:
            for key, name in (("preview", "Ngày cần bản xem trước"), ("final", "Ngày cần bản chính thức")):
                d = parse_date(value.get(key))
                if d and d < today:
                    errors.append(f"{name} đã qua ({d.strftime('%d/%m/%Y')}).")
    if code == "A10":
        tracks = value.get("tracks", {})
        if any("OTHER" in (tracks.get(r) or []) for r in tracks) and not nonempty(value.get("other_lang")):
            errors.append("Đã chọn “Ngôn ngữ khác” thì cần ghi rõ là ngôn ngữ nào.")
        if all((tracks.get(r) or []) == ["NONE"] for r in ("TEXT", "VOICE", "SUB")):
            errors.append("Cả ba phần đều “Không dùng”: video không có chữ, giọng đọc lẫn phụ đề. Xác nhận lại với khách.")
    if code in {"C2.2", "C2.3", "C3.2", "C3.3", "C5.1", "B3.4", "B7.2"} and value.get("has") == "YES":
        follow = {"C2.2": "until", "C2.3": "text", "C3.2": "names", "C3.3": "day", "C5.1": "ref", "B3.4": "checker",
                  "B7.2": "list"}[code]
        field = next(f for f in question["fields"] if f["id"] == follow)
        if _empty(field, value.get(follow)):
            errors.append(f"Đã chọn “Có” thì cần điền “{field['label'] or 'chi tiết'}”.")
    if code == "C6.2" and value.get("v") == "HIRE" and not nonempty(value.get("spec")):
        errors.append("Cần thuê diễn viên thì cần ghi giới tính, độ tuổi, ngoại hình.")
    if code == "C1.2" and value.get("series") == "SERIES" and not nonempty(value.get("previous")):
        errors.append("Là một tập trong loạt thì cần link tập trước.")
    if code == "E1":
        for res in value.get("v", []) + ([value.get("v__other")] if "OTHER" in value.get("v", []) else []):
            if res != "OTHER" and resolution_ratio(res) is None:
                errors.append(f"Độ phân giải “{res}” cần dạng RộngxCao, ví dụ 1080x1920.")
    return errors


def resolution_ratio(text):
    match = re.fullmatch(r"\s*(\d{2,5})\s*[x×]\s*(\d{2,5})\s*", text or "")
    if not match:
        return None
    w, h = int(match.group(1)), int(match.group(2))
    g = math.gcd(w, h)
    return f"{w // g}:{h // g}"


def _root(answers):
    return {a["question_code"]: a for a in answers if not a.get("scope_id")}


def _val(root, code, field=None):
    a = root.get(code)
    value = a.get("value") if a else None
    if field is None:
        return value
    return value.get(field) if isinstance(value, dict) else None


def _str(root, code, field):
    """Giá trị chữ của một trường lựa chọn đơn; None nếu sai kiểu."""
    v = _val(root, code, field)
    return v if isinstance(v, str) else None


def _in(x, options):
    return isinstance(x, str) and x in options


def _list(x):
    return [v for v in x if isinstance(v, str)] if isinstance(x, list) else []


def active_groups(answers):
    root = _root(answers)
    groups = set(ALWAYS_GROUPS)
    p1 = _str(root, "P1", "v")
    if p1 == "FIRST":
        groups.add("B1")
    if p1 in {"OFTEN", "AGENCY"}:
        groups.add("B3")
    p2 = _list(_val(root, "P2", "v"))
    for key, group in (("BRIEF", "B2"), ("OLD_VIDEO", "B4"), ("SAMPLE", "B5")):
        if key in p2:
            groups.add(group)
    if _str(root, "P4", "v") == "D3":
        groups.add("B6")
    for key, group in (("SNS", "C1"), ("ADS", "C2"), ("CORP", "C3"), ("MOTION", "C4"), ("AI", "C5"), ("SHOOT", "C6")):
        if key in _list(_val(root, "P3", "v")):
            groups.add(group)
    tracks = _val(root, "A10", "tracks")
    tracks = tracks if isinstance(tracks, dict) else {}
    if any(lang in {"EN", "OTHER"} for row in tracks.values() for lang in _list(row)):
        groups.add("B7")
    voice = _list(tracks.get("VOICE"))
    assets = _val(root, "A12", "assets")
    assets = assets if isinstance(assets, dict) else {}
    if any(x != "NONE" for x in voice) or _in(assets.get("MUSIC"), {"HAVE", "NEW"}) or _in(assets.get("VOICE"), {"HAVE", "NEW"}):
        groups.add("C7")
    return groups


def is_lite(answers):
    root = _root(answers)
    return _str(root, "P1", "v") == "FIRST" or _str(root, "P4", "v") == "D3"


def is_required(question, answers, groups=None):
    groups = groups if groups is not None else active_groups(answers)
    if question["code"] == "D1":
        return "B4" in groups or _str(_root(answers), "C7.3", "v") == "YES"
    if question["group"] == "A" and not question.get("star") and is_lite(answers):
        return False
    return bool(question.get("required", True))


def applicable_codes(answers):
    groups = active_groups(answers)
    return [q["code"] for q in QUESTIONS if q["group"] in groups]


def valid_scope_ids(answers):
    """Bộ câu hỏi v3 không còn trả lời theo từng dòng bàn giao; yêu cầu theo cảnh nằm ở D1."""
    return set()


def annotate_answers(answers):
    """Giữ lịch sử, đánh dấu câu thuộc nhánh không còn áp dụng hoặc mẫu cũ."""
    applicable = set(applicable_codes(answers))
    result = []
    for answer in answers:
        a = dict(answer)
        code = a["question_code"]
        reason = None
        if code not in CATALOG:
            reason = "LEGACY_TEMPLATE"
        elif a.get("scope_id"):
            reason = "ORPHANED_SCOPE"
        elif code not in applicable:
            reason = "BRANCH_NOT_APPLICABLE"
        a["applicable"] = reason is None
        if reason:
            a["inactive_reason"] = reason
        else:
            a.pop("inactive_reason", None)
        result.append(a)
    return result


def cross_checks(answers):
    """Kiểm tra giữa các câu. Không phụ thuộc ngày hiện tại để snapshot ổn định."""
    root = _root(answers)
    blockers, notes = [], []
    groups = active_groups(answers)
    ratios = [r for r in _list(_val(root, "A7", "ratios")) if r != "OTHER"]
    e1 = _val(root, "E1")
    if ratios and isinstance(e1, dict) and isinstance(e1.get("v"), list):
        chosen = [r for r in _list(e1.get("v")) if r != "OTHER"]
        if "OTHER" in _list(e1.get("v")) and nonempty(e1.get("v__other")):
            chosen += [x.strip() for x in e1["v__other"].split(",") if x.strip()]
        res_ratios = {res: resolution_ratio(res) for res in chosen}
        for res, ratio in res_ratios.items():
            if ratio and ratio not in ratios:
                blockers.append(("E1", f"Độ phân giải {res} có tỷ lệ {ratio}, không khớp khung hình khách chọn ở A7 "
                                       f"({', '.join(ratios)}). Ví dụ: dọc 9:16 là 1080×1920, không phải 1920×1080."))
        for ratio in ratios:
            if ratio not in res_ratios.values():
                blockers.append(("E1", f"Khung hình {ratio} ở A7 chưa có độ phân giải xuất tương ứng."))
    if "AI" in _list(_val(root, "P3", "v")) and _str(root, "A17", "v") == "NO":
        blockers.append(("A17", "Khách chọn “Video tạo bằng AI” ở P3 nhưng ở A17 lại không cho dùng AI. Hỏi lại khách."))
    e10 = _str(root, "E10", "status")
    if e10 == "UNCLEAR":
        blockers.append(("E10", "Quyền dùng tài nguyên chưa rõ; chưa đưa tài nguyên vào sản xuất."))
    elif e10 == "CLAIMED":
        notes.append(("E10", "Quyền dùng tài nguyên mới là khách tự khai, chưa có giấy tờ."))
    owner = _str(root, "A18", "owner")
    if owner in {"WEB", "UNSURE"} and e10 == "VERIFIED":
        notes.append(("E10", "A18 ghi tài nguyên lấy trên mạng hoặc chưa chắc, nhưng E10 ghi đã xác minh. Ghi rõ bằng chứng."))
    if owner == "BOUGHT" and not nonempty(_val(root, "A18", "proof")):
        notes.append(("A18", "Khách ghi đã mua quyền nhưng chưa gửi giấy tờ."))
    where = set(_list(_val(root, "A9", "where")))
    if _str(root, "A8", "length") == "GT3" and where and where <= {"TIKTOK", "SHORTS"}:
        notes.append(("A8", "Video trên 3 phút nhưng chỉ đăng TikTok/YouTube Shorts: kiểm tra giới hạn thời lượng hiện tại của kênh."))
    if "B6" in groups and _str(root, "P4", "v") == "D3" and _str(root, "A8", "length") in {"M1_3", "GT3"}:
        notes.append(("B6", "Khách cần trong 3 ngày nhưng video dài trên 1 phút: thống nhất phần bớt ở B6.1."))
    if "B6" in groups and _list(_val(root, "B6.1", "v")) == ["NONE"]:
        notes.append(("B6.1", "Khách cần gấp nhưng không chấp nhận bớt phần nào: báo rõ rủi ro trễ hạn."))
    d1 = _val(root, "D1", "rows")
    if isinstance(d1, list):
        key = lambda r: (r.get("object") if isinstance(r.get("object"), str) else "", _norm(r.get("detail")))
        alls = {key(r): r for r in d1 if isinstance(r, dict) and r.get("scope") == "ALL"}
        for i, r in enumerate(d1, 1):
            if isinstance(r, dict) and r.get("scope") != "ALL" and key(r) in alls:
                base = alls[key(r)]
                if base.get("action") != r.get("action") and not nonempty(r.get("note")):
                    notes.append(("D1", f"Dòng {i} ({scope_text(r)}) khác yêu cầu “Toàn video” cho “{r.get('detail')}”: "
                                        f"ghi ở cột Ghi chú đây là ngoại lệ."))
    return blockers, notes


def evaluate(answers):
    answers = annotate_answers(answers)
    root = _root(answers)
    groups = active_groups(answers)
    applicable = [q["code"] for q in QUESTIONS if q["group"] in groups]
    blockers, clarifications = [], []
    required_total = required_done = 0
    sections = {s["id"]: {"id": s["id"], "applicable": False, "total": 0, "required": 0, "answered": 0, "confirmed": 0,
                          "issues": 0} for s in SECTIONS}

    def add(code, message, severity="BLOCKER", reason="ANSWER_REQUIRED"):
        owner = "PM" if reason not in {"ANSWER_REQUIRED"} else "ACCOUNT"
        entry = {"code": reason, "question_code": code, "scope_id": "", "message": message, "severity": severity,
                 "owner_role": owner}
        (blockers if severity == "BLOCKER" else clarifications).append(entry)
        section = CATALOG.get(code, {}).get("section")
        if section in sections and severity == "BLOCKER" and reason not in {"ANSWER_REQUIRED", "NEEDS_CONFIRMATION"}:
            sections[section]["issues"] += 1

    for code in applicable:
        q = CATALOG[code]
        need = is_required(q, answers, groups)
        sec = sections[q["section"]]
        sec["applicable"] = True
        sec["total"] += 1
        sec["required"] += int(need)
        required_total += int(need)
        a = root.get(code)
        answered = bool(a) and a.get("status") not in {"UNANSWERED"} and a.get("value") not in (None, "", {})
        sec["answered"] += int(answered or bool(a and a.get("status") == "NEEDS_CONSULTATION"))
        if not a:
            if need:
                add(code, "Chưa có câu trả lời.")
            continue
        status = a["status"]
        if status == "NEEDS_CONSULTATION":
            add(code, "Khách cần tư vấn câu này; người phụ trách đề xuất rồi khách xác nhận.", reason="NEEDS_CONSULTATION")
            continue
        if status == "CONFLICTED":
            add(code, "Có giá trị mâu thuẫn chưa được giải quyết.", reason="ANSWER_CONFLICTED")
            continue
        if status in {"UNKNOWN", "NOT_APPLICABLE"}:
            if need:
                add(code, "Câu bắt buộc chưa có câu trả lời rõ.", reason="ANSWER_UNCLEAR")
            continue
        errors = semantic_errors(code, a["value"])
        for error in errors:
            add(code, error, reason="INVALID_ANSWER")
        if errors:
            continue
        if status != "CONFIRMED":
            add(code, "Câu trả lời chưa được người phụ trách xác nhận.", reason="NEEDS_CONFIRMATION")
            continue
        sec["confirmed"] += 1
        required_done += int(need)
    cross_blockers, cross_notes = cross_checks(answers)
    for code, message in cross_blockers:
        add(code, message, reason="CROSS_FIELD")
    for code, message in cross_notes:
        add(code, message, severity="INFO", reason="CROSS_FIELD_NOTE")
    for a in answers:
        if a.get("inactive_reason") == "LEGACY_TEMPLATE":
            add(a["question_code"], "Câu trả lời của bộ câu hỏi cũ; giữ trong lịch sử, không dùng cho sản xuất.",
                severity="INFO", reason="LEGACY_ANSWER_INACTIVE")
    completion = round(required_done / required_total * 100) if required_total else 0
    return {"can_submit": not blockers, "blockers": blockers, "clarifications": clarifications,
            "applicable_codes": applicable, "required_codes": [c for c in applicable if is_required(CATALOG[c], answers, groups)],
            "active_groups": sorted(groups), "lite_mode": is_lite(answers), "completion": completion,
            "sections": [s for s in sections.values()], "policy_version": POLICY_VERSION}


def delivery_matrix(answers):
    root = _root(answers)
    a7 = _val(root, "A7")
    count = a7.get("count") if isinstance(a7, dict) else None
    ratios = [r for r in _list(a7.get("ratios")) if r != "OTHER"] if isinstance(a7, dict) else []
    if not is_number(count) or int(count) != count or count < 1:
        return {"items": [], "total_base": 0, "total_files": 0, "variant_policy": "CHƯA XÁC NHẬN"}
    count = int(count)
    policy = _str(root, "E2", "v")
    tracks = _val(root, "A10", "tracks")
    languages = sorted({x for row in (tracks.values() if isinstance(tracks, dict) else []) for x in _list(row) if x != "NONE"})
    length = _str(root, "A8", "length")
    length_label = _label(next(f for f in CATALOG["A8"]["fields"] if f["id"] == "length")["options"], length) if length else None
    per_video = len(ratios) if policy == "EACH_RATIO" and ratios else 1
    policy_label = {"EACH_RATIO": "Mỗi khung hình là một video riêng",
                    "ONE_PER_VIDEO": "Mỗi video tính một, dù nhiều khung hình"}.get(policy, "CHƯA XÁC NHẬN")
    items = [{"id": "VIDEO", "quantity": count, "aspect_ratios": ratios, "duration": length_label, "languages": languages}]
    return {"items": items, "total_base": count, "total_files": count * max(1, len(ratios) or 1),
            "total_counted": count * per_video, "variant_policy": policy_label,
            "counting_rule": "Số file = số video × số khung hình; số video tính tiền theo E2."}


# ---------- Hiển thị câu trả lời thành chữ (dùng cho bản xuất) ----------

def _field_text(field, value):
    raw = value.get(field["id"])
    kind = field["type"]
    if _empty(field, raw):
        return None
    if kind in {"text", "textarea", "date"}:
        if kind == "date" and parse_date(raw):
            return parse_date(raw).strftime("%d/%m/%Y")
        return str(raw)
    if kind == "number":
        n = int(raw) if is_number(raw) and int(raw) == raw else raw
        text = f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n)
        return f"{text} {field.get('unit', '')}".strip()
    if kind == "single":
        if raw == "OTHER":
            return f"Khác: {value.get(field['id'] + '__other', '')}"
        return _label(field["options"], raw)
    if kind == "multi":
        parts = [(_label(field["options"], x) if x != "OTHER" else f"Khác: {value.get(field['id'] + '__other', '')}")
                 for x in _list(raw)]
        return ", ".join(parts)
    if kind == "matrix_single":
        return "; ".join(f"{r['label']}: {_label(field['cols'], raw.get(r['id']))}" for r in field["rows"]
                         if isinstance(raw, dict) and raw.get(r["id"]))
    if kind == "matrix_multi":
        return "; ".join(f"{r['label']}: {', '.join(_label(field['cols'], x) for x in _list(raw.get(r['id'])))}"
                         for r in field["rows"] if isinstance(raw, dict) and raw.get(r["id"]))
    if kind == "scene_table":
        lines = []
        for row in raw if isinstance(raw, list) else []:
            if not isinstance(row, dict):
                continue
            line = f"{scope_text(row)} · {_label(field['objects'], row.get('object'))} · {row.get('detail', '')} · " \
                   f"{_label(field['actions'], row.get('action'))}"
            if nonempty(row.get("value")):
                line += f" → {row['value']}"
            if nonempty(row.get("note")):
                line += f" ({row['note']})"
            lines.append(line)
        return "\n".join(lines)
    return str(raw)


def answer_rows(code, value):
    """[(nhãn trường, chữ)] cho một câu trả lời; an toàn với dữ liệu sai kiểu."""
    q = CATALOG.get(code)
    if not q:
        return [("Giá trị (mẫu cũ)", value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))]
    if isinstance(value, dict) and value.get("_na") is True:
        return [("", "Không áp dụng")]
    if not isinstance(value, dict):
        return [("", value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))] if value not in (None, "") else []
    rows = []
    for field in q["fields"]:
        try:
            text = _field_text(field, value)
        except Exception:
            text = json.dumps(value.get(field["id"]), ensure_ascii=False)
        if text:
            rows.append((field.get("label", ""), text))
    return rows


def answer_text(code, value):
    return "\n".join(f"{label}: {text}" if label else text for label, text in answer_rows(code, value))
