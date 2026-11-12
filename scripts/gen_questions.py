"""Sinh backend/app/questions.json (bộ câu hỏi v3, rẽ nhánh theo kiểu khách).

Chạy: python3 gen_questions.py <đường dẫn questions.json>
"""
import json
import sys


def o(*pairs):
    return [{"id": i, "label": l} for i, l in pairs]


def text(fid, label="", example="", required=True, multiline=False, max_len=2000):
    return {"id": fid, "type": "textarea" if multiline else "text", "label": label, "example": example,
            "required": required, "max_length": max_len}


def single(fid, options, label="", other=False, required=True):
    return {"id": fid, "type": "single", "label": label, "options": options, "other": other, "required": required}


def multi(fid, options, label="", other=False, required=True, max_items=None, exclusive=()):
    f = {"id": fid, "type": "multi", "label": label, "options": options, "other": other, "required": required}
    if max_items:
        f["max_items"] = max_items
    if exclusive:
        f["exclusive"] = list(exclusive)
    return f


def number(fid, label="", unit="", minimum=0, maximum=100000, integer=True, required=True):
    return {"id": fid, "type": "number", "label": label, "unit": unit, "min": minimum, "max": maximum,
            "integer": integer, "required": required}


def date(fid, label="", required=True):
    return {"id": fid, "type": "date", "label": label, "required": required}


Q = []


def q(code, group, section, label, fields, star=False, help="", allow_na=False, audience="client", required=True,
      note=""):
    Q.append({"code": code, "group": group, "section": section, "label": label, "help_text": help, "note": note,
              "required": required, "star": star, "allow_na": allow_na, "audience": audience,
              "value_type": "json", "fields": fields})


YES_NO = o(("YES", "Có"), ("NO", "Không"))

# ---------------- Phần 0 ----------------
S0 = "P"
q("P1", "P", S0, "Bạn đã từng đặt làm video chưa?", [single("v", o(
    ("FIRST", "Lần đầu"), ("FEW", "Đã làm vài lần"), ("OFTEN", "Làm thường xuyên"),
    ("AGENCY", "Tôi là agency, làm cho khách của tôi")))], star=True)
q("P2", "P", S0, "Hiện bạn đang có gì trong tay?", [multi("v", o(
    ("IDEA", "Mới có ý tưởng"), ("BRIEF", "Có brief hoặc kịch bản viết sẵn"),
    ("OLD_VIDEO", "Có video cũ cần sửa hoặc làm lại"), ("SAMPLE", "Có video mẫu muốn làm giống")))],
  star=True, help="Chọn được nhiều mục.")
q("P3", "P", S0, "Bạn cần loại video nào?", [multi("v", o(
    ("SNS", "Video ngắn đăng mạng xã hội"), ("ADS", "Quảng cáo chạy trả phí"),
    ("CORP", "Giới thiệu doanh nghiệp hoặc sự kiện"), ("MOTION", "Đồ họa chuyển động, màn hình LED"),
    ("AI", "Video tạo bằng AI"), ("SHOOT", "Có quay thật"), ("UNSURE", "Chưa biết – cần tư vấn")),
    exclusive=("UNSURE",))], star=True, help="Chọn được nhiều mục.")
q("P4", "P", S0, "Khi nào bạn cần video?", [single("v", o(
    ("D3", "Trong 3 ngày"), ("W2", "Trong 1–2 tuần"), ("LATER", "Hơn 2 tuần"), ("OPEN", "Chưa có hạn")))],
  star=True)

# ---------------- Phần A ----------------
q("A1", "A", "A-WHO", "Tên dự án và đơn vị của bạn?", [
    text("project", "Tên dự án", "Khai trương chi nhánh 2"),
    text("org", "Đơn vị", "Quán cà phê Nắng")], star=True)
q("A2", "A", "A-WHO", "Ai là người trao đổi chính, liên hệ qua đâu?", [
    text("name", "Họ tên", "Nguyễn Văn A"),
    single("channel", o(("ZALO", "Zalo"), ("PHONE", "Điện thoại"), ("EMAIL", "Email"), ("MESSENGER", "Messenger")),
           "Kênh liên hệ"),
    text("contact", "Số hoặc địa chỉ", "0901 234 567")], star=True)
q("A3", "A", "A-WHY", "Video này dùng để làm gì?", [single("v", o(
    ("SELL", "Bán hàng"), ("BRAND", "Giới thiệu thương hiệu"), ("EVENT", "Thông báo sự kiện, khuyến mãi"),
    ("HIRE", "Tuyển dụng"), ("GUIDE", "Hướng dẫn, đào tạo")), other=True)], star=True,
  help="Chọn một mục chính.")
q("A4", "A", "A-WHY", "Ai sẽ xem video?", [
    text("age", "Độ tuổi", "18–30"),
    single("gender", o(("M", "Nam"), ("F", "Nữ"), ("ALL", "Cả hai")), "Giới tính"),
    text("area", "Khu vực", "TP.HCM", required=False)])
q("A5", "A", "A-WHY", "Ba điều nhất định phải có trong video?", [
    text("p1", "Điều 1", "Giá 49k"), text("p2", "Điều 2", "Giao trong 30 phút", required=False),
    text("p3", "Điều 3", "Địa chỉ quán", required=False)], star=True)
q("A6", "A", "A-WHY", "Xem xong, bạn muốn người xem làm gì?", [
    single("action", o(("BUY", "Mua hàng"), ("CONTACT", "Nhắn tin hoặc gọi điện"), ("WEB", "Vào website"),
                       ("SIGNUP", "Đăng ký"), ("REMEMBER", "Chỉ cần nhớ thương hiệu")), other=True),
    text("exact", "Thông tin phải hiện đúng từng chữ", "0901 234 567 · nangcoffee.vn · NANG10", required=False)],
  star=True, help="Thông tin phải hiện đúng từng chữ: số điện thoại, link, mã giảm giá.")
q("A7", "A", "A-LOOK", "Bạn cần bao nhiêu video, khung hình nào?", [
    number("count", "Số video", "video", 1, 500),
    multi("ratios", o(("9:16", "Dọc 9:16"), ("16:9", "Ngang 16:9"), ("1:1", "Vuông 1:1"), ("4:5", "4:5")),
          "Khung hình")], star=True,
  note="[bạn điền] Quy ước mỗi khung hình hoặc ngôn ngữ thêm có tính là một video riêng hay không.")
q("A8", "A", "A-LOOK", "Mỗi video dài bao lâu?", [
    single("length", o(("LT15", "Dưới 15 giây"), ("S15_30", "15–30 giây"), ("S30_60", "30–60 giây"),
                       ("M1_3", "1–3 phút"), ("GT3", "Trên 3 phút")), "Thời lượng"),
    single("strict", o(("STRICT", "Bắt buộc đúng"), ("FLEX", "Xê dịch được")), "Mức linh hoạt")], star=True)
q("A9", "A", "A-LOOK", "Video sẽ đăng ở đâu?", [
    multi("where", o(("TIKTOK", "TikTok"), ("META", "Facebook, Instagram"), ("SHORTS", "YouTube Shorts"),
                     ("YOUTUBE", "YouTube video dài"), ("WEB", "Website"), ("LED", "Màn hình LED, sự kiện"),
                     ("TV", "TV")), "Nơi đăng"),
    text("main", "Kênh quan trọng nhất", "TikTok", required=False)], star=True)
q("A10", "A", "A-LOOK", "Ngôn ngữ trong video?", [{
    "id": "tracks", "type": "matrix_multi", "label": "Ngôn ngữ theo từng phần",
    "rows": o(("TEXT", "Chữ trên màn hình"), ("VOICE", "Giọng đọc"), ("SUB", "Phụ đề")),
    "cols": o(("VI", "Tiếng Việt"), ("EN", "Tiếng Anh"), ("OTHER", "Ngôn ngữ khác"), ("NONE", "Không dùng")),
    "exclusive": ["NONE"], "required": True},
    text("other_lang", "Ngôn ngữ khác là gì", "Tiếng Nhật", required=False)])
q("A11", "A", "A-LOOK", "Bạn muốn video mang cảm giác gì?", [
    multi("mood", o(("FUN", "Vui, trẻ trung"), ("LUX", "Sang trọng"), ("MOVING", "Cảm động"),
                    ("TECH", "Công nghệ, hiện đại"), ("REAL", "Chân thực, đời thường")), "Cảm giác", max_items=2),
    text("links", "Link 1–3 video bạn thích", "https://…", required=False, multiline=True),
    text("like", "Thích điểm gì", "Nhịp nhanh, chữ to", required=False),
    text("dislike", "Không thích điểm gì", "Nhạc quá ồn", required=False)], star=True,
  help="Chọn tối đa hai.")
q("A12", "A", "A-HAVE", "Những thứ sau bạn đã có chưa?", [{
    "id": "assets", "type": "matrix_single", "label": "Tài nguyên",
    "rows": o(("LOGO", "Logo"), ("PRODUCT", "Ảnh hoặc video sản phẩm"), ("SCRIPT", "Kịch bản, lời thoại"),
              ("BRAND", "Quy định màu sắc, kiểu chữ thương hiệu"), ("MUSIC", "Nhạc"), ("VOICE", "Giọng đọc")),
    "cols": o(("HAVE", "Đã có, sẽ gửi"), ("NEW", "Cần làm mới"), ("NO", "Không cần")), "required": True}])
q("A13", "A", "A-HAVE", "Có điều gì không được xuất hiện, hoặc câu chữ nào phải giữ nguyên?", [
    text("forbidden", "Không được có", "Không nhắc tên đối thủ", required=False, multiline=True),
    text("verbatim", "Phải giữ nguyên văn", "Slogan: “Ngon từ hạt đầu tiên”", required=False, multiline=True)],
  allow_na=True)
q("A14", "A", "A-PLAN", "Các mốc thời gian?", [
    date("preview", "Cần bản xem trước"), date("final", "Cần bản chính thức"),
    date("publish", "Ngày đăng (nếu đã có)", required=False)], star=True,
  help="Mặc định giờ Việt Nam; múi giờ chỉ hỏi khi khách ở nước ngoài.")
q("A15", "A", "A-PLAN", "Ngân sách dự kiến?", [single("range", o(
    ("R1", "Dưới 5 triệu đồng"), ("R2", "5–15 triệu đồng"), ("R3", "15–50 triệu đồng"), ("R4", "Trên 50 triệu đồng"),
    ("QUOTE", "Chưa có – cần báo giá trước")))],
  note="[bạn điền] Thay các khoảng giá bằng bảng giá thật của bạn.")
q("A16", "A", "A-PLAN", "Ai là người duyệt bản cuối?", [
    text("name", "Họ tên", "Chị Lan – chủ quán"),
    single("mode", o(("ONE", "Một người quyết"), ("MANY", "Nhiều người cùng duyệt")), "Cách duyệt")])
q("A17", "A", "A-RIGHTS", "Bạn có cho phép dùng AI để tạo hình ảnh, video, giọng đọc không?", [single("v", o(
    ("YES", "Được"), ("NO_REAL_PEOPLE", "Được, nhưng không tạo người thật hoặc giọng người thật"),
    ("NO", "Không dùng AI")))])
q("A18", "A", "A-RIGHTS", "Ảnh, nhạc, giọng, hình người bạn gửi là của ai?", [
    single("owner", o(("OWN", "Của tôi hoặc công ty tôi"), ("BOUGHT", "Đã mua, có giấy tờ"),
                      ("WEB", "Lấy trên mạng"), ("UNSURE", "Chưa chắc")), "Nguồn gốc"),
    text("proof", "Link hoặc tên file giấy tờ (nếu đã mua)", "giay-phep-nhac.pdf", required=False)],
  allow_na=True,
  help="Nếu chọn “đã mua” thì gửi kèm bản chụp giấy tờ; hai lựa chọn cuối nghĩa là chưa được dùng cho đến khi làm rõ.")

# ---------------- Phần B ----------------
q("B1.1", "B1", "B1", "Bạn muốn được tư vấn phần nào?", [multi("v", o(
    ("TYPE", "Nên làm loại video gì"), ("LEN", "Nên dài bao lâu, đăng ở đâu"), ("CONTENT", "Nội dung, kịch bản"),
    ("COST", "Chi phí"), ("ALL", "Tất cả")), exclusive=("ALL",))])
q("B1.2", "B1", "B1", "Bạn muốn trao đổi theo cách nào?", [single("v", o(
    ("FORM", "Tự điền phiếu này"), ("CALL", "Gọi khoảng 15 phút để được hỏi trực tiếp"), ("CHAT", "Nhắn tin")))])
q("B2.1", "B2", "B2", "Gửi file brief hoặc kịch bản.", [
    text("link", "Link hoặc tên file", "Tải lên ở tab Tài liệu nguồn, rồi ghi tên file ở đây")])
q("B2.2", "B2", "B2", "Tài liệu này đã được người quyết định duyệt chưa?", [single("v", o(
    ("FINAL", "Đã duyệt, không đổi nữa"), ("APPROVED_EDITABLE", "Đã duyệt, còn sửa được"), ("DRAFT", "Bản nháp")))])
q("B2.3", "B2", "B2", "Phần nào bạn muốn mình góp ý hoặc viết lại?", [multi("v", o(
    ("NONE", "Không, làm đúng theo tài liệu"), ("DIALOG", "Lời thoại"), ("SCENES", "Phân cảnh"), ("ALL", "Toàn bộ")),
    exclusive=("NONE", "ALL"))])
q("B3.1", "B3", "B3", "Video phải qua mấy cấp duyệt?", [
    single("levels", o(("1", "Một"), ("2", "Hai"), ("3+", "Ba trở lên")), "Số cấp"),
    text("people", "Tên và vai trò từng người", "Anh Minh – Marketing; Chị Hà – Giám đốc", multiline=True)])
q("B3.2", "B3", "B3", "Mỗi lần gửi bản xem, bao lâu bên bạn phản hồi?", [single("v", o(
    ("SAME_DAY", "Trong ngày"), ("D1_2", "1–2 ngày"), ("D3_5", "3–5 ngày"), ("LONGER", "Lâu hơn")))])
q("B3.3", "B3", "B3", "Bạn cần giấy tờ gì?", [multi("v", o(
    ("CONTRACT", "Hợp đồng"), ("INVOICE", "Hóa đơn"), ("NDA", "Cam kết bảo mật"), ("NONE", "Không cần")),
    exclusive=("NONE",))])
q("B3.4", "B3", "B3", "Có số liệu, tên người, chức danh, chứng nhận nào phải đúng tuyệt đối không?", [
    single("has", YES_NO), text("checker", "Người xác nhận", "Chị Hà – Giám đốc", required=False)])
q("B3.5", "B3", "B3", "(Chỉ agency) Khách cuối là ai, và ai là người nói chuyện với họ?", [
    text("end_client", "Khách cuối", "Thương hiệu X", required=False),
    single("contact", o(("AGENCY", "Agency làm đầu mối"), ("DIRECT", "Mình được trao đổi trực tiếp")),
           "Đầu mối", required=False)], required=False)
q("B4.1", "B4", "B4", "Gửi video hiện có.", [
    text("link", "Link hoặc tên file", "Tải lên ở tab Tài liệu nguồn, rồi ghi tên file ở đây")])
q("B4.2", "B4", "B4", "Bạn muốn làm gì với video này?", [single("v", o(
    ("FIX", "Sửa vài chỗ"), ("REMAKE", "Làm lại, giữ ý tưởng"), ("REFORMAT", "Chỉ đổi khung hình hoặc ngôn ngữ"),
    ("CUT", "Cắt ngắn lại")))])
q("B4.3", "B4", "B4", "Bạn có file dự án gốc không?", [single("v", o(
    ("YES", "Có"), ("NO", "Không"), ("UNKNOWN", "Không biết")))],
  help="File dựng (ví dụ file Premiere, CapCut), không phải file video đã xuất.")
q("B5.1", "B5", "B5", "Link video mẫu", [text("v", "Link", "https://…")])
q("B5.2", "B5", "B5", "Bạn muốn giống ở điểm nào?", [multi("v", o(
    ("PACE", "Nhịp nhanh chậm"), ("COLOR", "Màu sắc"), ("TRANSITION", "Cách chuyển cảnh"), ("FRAMING", "Bố cục khung hình"),
    ("TYPE", "Kiểu chữ"), ("MUSIC", "Nhạc"), ("STORY", "Cách kể chuyện")))])
q("B5.3", "B5", "B5", "Điểm nào phải khác video mẫu?", [
    text("v", "", "Không dùng màu tím; nhân vật là nữ", multiline=True)], allow_na=True)
q("B6.1", "B6", "B6", "Để kịp hạn, bạn chấp nhận bớt phần nào?", [multi("v", o(
    ("ROUNDS", "Ít vòng sửa hơn"), ("SHORTER", "Video ngắn hơn"), ("STOCK", "Dùng hình, nhạc có sẵn"),
    ("ONE_RATIO", "Chỉ một khung hình"), ("NONE", "Không bớt được gì")), exclusive=("NONE",))])
q("B6.2", "B6", "B6", "Ai bên bạn trả lời được ngay trong ngày?", [
    text("v", "Tên và cách liên hệ", "Anh Minh – 0901 234 567")])
q("B7.1", "B7", "B7", "Ai duyệt bản dịch và chính tả của từng ngôn ngữ?", [
    text("v", "", "Tiếng Anh: chị Mai; tiếng Nhật: anh Ken", multiline=True)])
q("B7.2", "B7", "B7", "Có tên riêng, thuật ngữ nào phải viết hoặc đọc theo cách cố định không?", [
    single("has", YES_NO), text("list", "Danh sách", "NATORI đọc là “na-tô-ri”", required=False, multiline=True)])
q("B7.3", "B7", "B7", "Bạn ở múi giờ nào?", [single("v", o(
    ("Asia/Ho_Chi_Minh", "Việt Nam (UTC+7)"), ("Asia/Tokyo", "Tokyo (UTC+9)"), ("Asia/Seoul", "Seoul (UTC+9)"),
    ("Asia/Singapore", "Singapore (UTC+8)"), ("Australia/Sydney", "Sydney"), ("Europe/London", "London"),
    ("Europe/Paris", "Paris, Berlin"), ("America/New_York", "New York"), ("America/Los_Angeles", "Los Angeles")),
    other=True)], help="Chọn thành phố gần bạn nhất.")

# ---------------- Phần C ----------------
q("C1.1", "C1", "C1", "Ba giây đầu cần có gì?", [single("v", o(
    ("QUESTION", "Câu hỏi gây tò mò"), ("OFFER", "Ưu đãi, giá"), ("PRODUCT", "Hình sản phẩm"),
    ("SUGGEST", "Để mình đề xuất")))])
q("C1.2", "C1", "C1", "Video này thuộc loạt nhiều tập không?", [
    single("series", o(("SINGLE", "Video lẻ"), ("SERIES", "Một tập trong loạt"))),
    text("previous", "Link tập trước", "https://…", required=False)])
q("C1.3", "C1", "C1", "Cần thêm những thứ sau không?", [multi("v", o(
    ("CAPTION", "Phụ đề chạy theo lời"), ("COVER", "Ảnh bìa"), ("HASHTAG", "Gợi ý caption và hashtag"),
    ("TREND", "Nhạc đang thịnh hành"), ("NONE", "Không cần")), exclusive=("NONE",))])
q("C2.1", "C2", "C2", "Một câu nói vì sao khách nên chọn bạn thay vì đối thủ:", [
    text("v", "", "Cà phê rang mỗi sáng, giao trong 30 phút")])
q("C2.2", "C2", "C2", "Có giá, khuyến mãi hoặc số liệu chỉ đúng trong một thời gian không?", [
    single("has", YES_NO), date("until", "Hết hạn ngày", required=False)])
q("C2.3", "C2", "C2", "Có dòng chữ pháp lý bắt buộc không?", [
    single("has", YES_NO), text("text", "Ghi nguyên văn", "Sản phẩm này không phải là thuốc…", required=False,
                                 multiline=True)],
  help="Ví dụ: “Sản phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh”.")
q("C2.4", "C2", "C2", "Cần mấy phiên bản để thử xem bản nào hiệu quả hơn?", [
    single("count", o(("1", "Một"), ("2", "Hai"), ("3+", "Ba trở lên")), "Số phiên bản"),
    multi("differ", o(("HOOK", "Câu mở đầu"), ("OFFER", "Ưu đãi"), ("CTA", "Lời kêu gọi cuối")),
          "Các bản khác nhau ở", required=False)])
q("C3.1", "C3", "C3", "Video kể về điều gì?", [single("v", o(
    ("FOUNDING", "Câu chuyện thành lập"), ("CAPABILITY", "Năng lực, dự án đã làm"), ("CULTURE", "Văn hóa, tuyển dụng"),
    ("EVENT", "Ghi lại sự kiện")), other=True)])
q("C3.2", "C3", "C3", "Có người phát biểu hoặc phỏng vấn không?", [
    single("has", YES_NO), number("count", "Số người", "người", 1, 100, required=False),
    text("names", "Tên, chức danh", "Ông Trần B – Giám đốc", required=False, multiline=True)])
q("C3.3", "C3", "C3", "Có ngày quay hoặc ngày sự kiện cố định không?", [
    single("has", YES_NO), date("day", "Ngày", required=False),
    single("permit", YES_NO, "Địa điểm cần xin phép", required=False)])
q("C4.1", "C4", "C4", "Video chiếu trên loại màn hình nào?", [
    single("screen", o(("NORMAL", "Màn hình thường"), ("STAGE_LED", "LED sân khấu"), ("MULTI", "Nhiều màn hình ghép"))),
    text("spec", "Sơ đồ và kích thước (nếu ghép)", "3 màn 1920×1080 ghép ngang", required=False)])
q("C4.2", "C4", "C4", "Bạn có file mẫu hoặc thiết kế gốc không?", [single("v", o(
    ("YES", "Có – gửi kèm"), ("NO", "Không, làm mới")))])
q("C4.3", "C4", "C4", "Video có cần chạy lặp liên tục không bị giật không?", [single("v", YES_NO)])
q("C4.4", "C4", "C4", "Bạn cần nhận gì khi bàn giao?", [single("v", o(
    ("VIDEO", "Chỉ file video"), ("PROJECT", "Video và file dự án để tự sửa sau")))])
q("C5.1", "C5", "C5", "Có nhân vật hoặc sản phẩm phải giống hệt ảnh thật không?", [
    single("has", YES_NO), text("ref", "Ảnh chuẩn (tên file)", "anh-san-pham-chuan.jpg", required=False)])
q("C5.2", "C5", "C5", "Những gì không được thay đổi giữa các cảnh?", [multi("v", o(
    ("FACE", "Khuôn mặt"), ("OUTFIT", "Quần áo"), ("LOGO", "Logo"), ("PRODUCT_COLOR", "Màu sản phẩm"),
    ("SETTING", "Bối cảnh")), other=True)], allow_na=True)
q("C5.3", "C5", "C5", "Nếu phải chọn, bạn ưu tiên gì?", [single("v", o(
    ("ACCURACY", "Giống đúng từng chi tiết, chấp nhận lâu và tốn hơn"), ("SPEED", "Nhanh, chấp nhận khác một chút")))])
q("C5.4", "C5", "C5", "Video có cần ghi chú là nội dung tạo bằng AI không?", [single("v", o(
    ("YES", "Có"), ("NO", "Không"), ("PLATFORM", "Theo quy định của nền tảng")))])
q("C6.1", "C6", "C6", "Quay ở mấy địa điểm, ở đâu?", [
    number("count", "Số địa điểm", "nơi", 1, 100), text("where", "Địa chỉ", "12 Lê Lợi, Pleiku", multiline=True)])
q("C6.2", "C6", "C6", "Cần diễn viên không?", [
    single("v", o(("NO", "Không"), ("OWN", "Bên bạn có người"), ("HIRE", "Cần thuê"))),
    text("spec", "Giới tính, độ tuổi, ngoại hình (nếu thuê)", "Nữ, 25–30 tuổi", required=False)])
q("C6.3", "C6", "C6", "Cần quay bằng flycam không?", [single("v", YES_NO)])
q("C6.4", "C6", "C6", "Ngày quay dự kiến", [
    date("day", "Ngày quay"), number("days", "Số ngày", "ngày", 1, 60)], allow_na=True)
q("C7.1", "C7", "C7", "Giọng đọc thế nào?", [
    single("gender", o(("M", "Nam"), ("F", "Nữ")), "Giới tính"),
    single("accent", o(("NORTH", "Bắc"), ("CENTRAL", "Trung"), ("SOUTH", "Nam")), "Giọng vùng"),
    single("speed", o(("SLOW", "Chậm"), ("MID", "Vừa"), ("FAST", "Nhanh")), "Tốc độ"),
    text("sample", "Link một giọng bạn thích", "https://…", required=False)])
q("C7.2", "C7", "C7", "Nhạc thế nào?", [
    single("style", o(("UPBEAT", "Sôi động"), ("SOFT", "Nhẹ nhàng"), ("EPIC", "Hùng tráng"), ("NONE", "Không nhạc")),
           "Kiểu nhạc"),
    text("track", "Bài cụ thể (nếu có)", "Tên bài – ca sĩ", required=False)])
q("C7.3", "C7", "C7", "Có âm thanh hiệu ứng nào bắt buộc không?", [single("v", o(
    ("NO", "Không"), ("YES", "Có – ghi vào bảng yêu cầu theo cảnh")))],
  help="Ví dụ: tiếng mưa, tiếng chuông.")

# ---------------- Phần D ----------------
q("D1", "D", "D", "Bảng yêu cầu theo cảnh", [{
    "id": "rows", "type": "scene_table", "label": "Yêu cầu",
    "scope_kinds": o(("SCENE", "Cảnh số"), ("TIME", "Từ giây … đến giây …"), ("ALL", "Toàn video"),
                     ("FROM", "Từ cảnh … trở đi")),
    "objects": o(("CHARACTER", "Nhân vật"), ("PRODUCT", "Sản phẩm"), ("LOGO", "Logo"), ("TEXT", "Chữ"),
                 ("VOICE", "Giọng đọc"), ("MUSIC", "Nhạc"), ("SFX", "Âm thanh hiệu ứng"), ("SETTING", "Bối cảnh"),
                 ("COLOR", "Màu sắc"), ("OTHER", "Khác")),
    "actions": o(("ON", "Bật (thêm vào)"), ("OFF", "Tắt (bỏ đi)"), ("KEEP", "Giữ nguyên"), ("CHANGE", "Đổi thành"),
                 ("ANY", "Không quan trọng"), ("UNKNOWN", "Chưa biết")),
    "required": True}], required=False,
  help="Mỗi dòng một đối tượng và một yêu cầu. Hai chi tiết của cùng nhân vật (màu mắt, kiểu tóc) là hai dòng.")

# ---------------- Phần E (nội bộ) ----------------
I = "internal"
q("E1", "E", "E", "Độ phân giải xuất file", [multi("v", o(
    ("1080x1920", "1080×1920 (9:16)"), ("2160x3840", "2160×3840 (9:16, 4K)"), ("1920x1080", "1920×1080 (16:9)"),
    ("3840x2160", "3840×2160 (16:9, 4K)"), ("1080x1080", "1080×1080 (1:1)"), ("1080x1350", "1080×1350 (4:5)")),
    other=True)], audience=I, help="Mỗi khung hình ở A7 cần ít nhất một độ phân giải khớp tỷ lệ.",
  note="Khác: ghi dạng RộngxCao, ví dụ 1440x2560.")
q("E2", "E", "E", "Cách tính số video bàn giao", [single("v", o(
    ("EACH_RATIO", "Mỗi khung hình là một video riêng"), ("ONE_PER_VIDEO", "Mỗi video tính một, dù nhiều khung hình")))],
  audience=I)
q("E3", "E", "E", "Codec, định dạng file, bitrate", [text("v", "", "H.264 MP4, 12 Mbps")], audience=I, required=False)
q("E4", "E", "E", "Vùng an toàn tránh nút và chữ của ứng dụng", [text("v", "", "Chừa 15% dưới cho TikTok")],
  audience=I, required=False)
q("E5", "E", "E", "Âm lượng chuẩn theo kênh đăng", [text("v", "", "-14 LUFS cho mạng xã hội")], audience=I,
  required=False)
q("E6", "E", "E", "Kế hoạch cảnh: số cảnh, cảnh dựng AI, cảnh dựng tay", [
    text("v", "", "8 cảnh; cảnh 2–4 dùng AI", multiline=True)], audience=I, required=False)
q("E7", "E", "E", "Cảnh cần tạo ảnh mẫu trước khi làm video", [text("v", "", "Cảnh 1, 5")], audience=I,
  required=False)
q("E8", "E", "E", "Lưu model, prompt, seed để làm lại được", [single("v", YES_NO)], audience=I, required=False)
q("E9", "E", "E", "Rủi ro AI tạo sai (tay, chữ, chuyển động)", [text("v", "", "Cảnh cầm ly dễ lỗi tay",
                                                                     multiline=True)], audience=I, required=False)
q("E10", "E", "E", "Quyền dùng tài nguyên (theo A18)", [
    single("status", o(("VERIFIED", "Đã xác minh"), ("CLAIMED", "Chỉ khách khai"), ("UNCLEAR", "Chưa rõ"))),
    text("evidence", "Bằng chứng hoặc việc cần làm", "Đã xem hóa đơn mua nhạc ngày 02/11", multiline=True)],
  audience=I)
q("E11", "E", "E", "Báo giá và số vòng sửa bao gồm", [
    number("amount", "Báo giá", "đồng", 0, 10_000_000_000),
    number("rounds", "Số vòng sửa", "vòng", 0, 20)], audience=I)
q("E12", "E", "E", "Công cụ dựng, mẫu, font, plugin", [text("v", "", "CapCut, font Be Vietnam Pro")], audience=I,
  required=False)

SECTIONS = [
    {"id": "P", "title": "Bắt đầu", "subtitle": "Bốn câu chọn đường đi phù hợp", "part": "Phần 0"},
    {"id": "A-WHO", "title": "Bạn là ai", "subtitle": "Thông tin liên hệ", "part": "Phần A"},
    {"id": "A-WHY", "title": "Video để làm gì", "subtitle": "Mục tiêu, người xem, thông điệp", "part": "Phần A"},
    {"id": "A-LOOK", "title": "Video trông thế nào", "subtitle": "Số lượng, thời lượng, nơi đăng, cảm giác",
     "part": "Phần A"},
    {"id": "A-HAVE", "title": "Bạn đã có gì", "subtitle": "Tài nguyên và giới hạn nội dung", "part": "Phần A"},
    {"id": "A-PLAN", "title": "Thời gian và chi phí", "subtitle": "Mốc, ngân sách, người duyệt", "part": "Phần A"},
    {"id": "A-RIGHTS", "title": "AI và quyền sử dụng", "subtitle": "Phạm vi dùng AI, nguồn gốc tài nguyên",
     "part": "Phần A"},
    {"id": "B1", "title": "Khách lần đầu", "subtitle": "Tư vấn từ đầu", "part": "Phần B"},
    {"id": "B2", "title": "Đã có brief", "subtitle": "Đối chiếu tài liệu sẵn có", "part": "Phần B"},
    {"id": "B3", "title": "Doanh nghiệp, agency", "subtitle": "Cấp duyệt và giấy tờ", "part": "Phần B"},
    {"id": "B4", "title": "Sửa video có sẵn", "subtitle": "Video gốc và chỗ cần sửa", "part": "Phần B"},
    {"id": "B5", "title": "Làm giống video mẫu", "subtitle": "Điểm giống, điểm khác", "part": "Phần B"},
    {"id": "B6", "title": "Cần gấp", "subtitle": "Phần chấp nhận bớt để kịp hạn", "part": "Phần B"},
    {"id": "B7", "title": "Nhiều ngôn ngữ", "subtitle": "Người duyệt bản dịch, múi giờ", "part": "Phần B"},
    {"id": "C1", "title": "Mạng xã hội", "subtitle": "Mở đầu, loạt tập, phụ đề", "part": "Phần C"},
    {"id": "C2", "title": "Quảng cáo trả phí", "subtitle": "Lợi thế, khuyến mãi, phiên bản thử", "part": "Phần C"},
    {"id": "C3", "title": "Doanh nghiệp, sự kiện", "subtitle": "Câu chuyện, người phát biểu", "part": "Phần C"},
    {"id": "C4", "title": "Đồ họa, LED", "subtitle": "Màn hình, file gốc, bàn giao", "part": "Phần C"},
    {"id": "C5", "title": "Video AI", "subtitle": "Độ giống, chi tiết cố định", "part": "Phần C"},
    {"id": "C6", "title": "Quay thật", "subtitle": "Địa điểm, diễn viên, ngày quay", "part": "Phần C"},
    {"id": "C7", "title": "Giọng đọc và nhạc", "subtitle": "Giọng, nhạc, hiệu ứng", "part": "Phần C"},
    {"id": "D", "title": "Yêu cầu theo cảnh", "subtitle": "Mỗi dòng một yêu cầu", "part": "Phần D"},
    {"id": "E", "title": "Phiếu nội bộ", "subtitle": "Người làm tự quyết, không hỏi khách", "part": "Phần E"},
]

if __name__ == "__main__":
    codes = [x["code"] for x in Q]
    assert len(codes) == len(set(codes)), "trùng mã"
    sec_ids = {s["id"] for s in SECTIONS}
    assert all(x["section"] in sec_ids for x in Q)
    out = {"template_version": "3.0.0-stage01", "sections": SECTIONS, "questions": Q}
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(len(Q), "câu,", len(SECTIONS), "mục")
