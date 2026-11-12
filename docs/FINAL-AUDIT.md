# Kiểm độc lập cuối — Stage 01 / Chặng A

Ngày 07/11/2026, Asia/Bangkok. Phạm vi: đọc backend/UI/contracts và kiểm hồi quy trên dữ liệu QA tách biệt; không phê duyệt khách hàng thật, không tạo video/provider/AE. Reviewer không triển khai bản backend ban đầu; sau phát hiện được giao sửa riêng questionnaire.py và viết tests/test_final_audit.py. Root sửa main.py/exports.py và tích hợp.

## Phát hiện và xử lý

| ID | Mức ban đầu | Bằng chứng trước sửa | Xử lý/kiểm lại |
| --- | --- | --- | --- |
| A01 | MAJOR | Source `CORE-02: NaN` → prefill HTTP 500 trong SQLite QA | Parser không lưu float phi hữu hạn: bare token giữ dạng text PROPOSED_FROM_SOURCE; structured JSON overflow trả 422. Bốn ca hồi quy đạt. |
| A02 | MAJOR | Mọi CORE chung đã confirm, thêm CORE-13 theo deliverable còn sai ngày/chưa confirm; can_submit true và submit 200 | Active scoped CORE override phải confirmed và semantic hợp lệ; invalid/pending bị chặn. Confirm đúng quyền giá trị hợp lệ mới mở điều kiện. |
| A03 | MAJOR | Variant ID của item A trùng ID item B vẫn semantic_errors=[]; scope_id không phân biệt được | Toàn bộ item/variant ID phải độc nhất trong ma trận; helper valid_scope_ids chỉ trả scope an toàn, không nhập nhằng. |
| A04 | MAJOR | Xóa/đổi item ID làm câu trả lời scope cũ còn xuất như requirement hiện hành | Giữ value/status/evidence/audit lịch sử; annotate applicable=false/inactive_reason=ORPHANED_SCOPE. Không dùng cho normalized active requirements/acceptance. Không chặn vĩnh viễn gate vì không có delete API. |
| A05 | MAJOR | Dữ liệu nháp item.id=[] có thể bị thêm vào set khi lưu scope, gây TypeError | Helper scope loại ID sai kiểu, rỗng, quá 100 ký tự và ID trùng; các ca malformed lookup/validation không crash. |
| A06 | Robustness | Lone Unicode surrogate có thể qua json.dumps ensure_ascii=false rồi lỗi serialize response | canonical kiểm UTF-8 trước lưu; root API bắt UnicodeError. Unit regression đạt. |

Ngoài ra, branch theo từng scope được phân biệt; scope đã bị loại không tự kích hoạt nhóm Nhật ngữ. Branch ẩn và orphan vẫn nằm trong lịch sử, không bị xóa. Nội dung snapshot/hash giữ bất biến; metadata historical bên ngoài phản ánh đúng hiệu lực hiện tại, không đánh đồng toàn bộ export envelope với phần canonical được duyệt.

## Kết quả thực chạy bởi reviewer

- Bộ hồi quy mới: **16 passed** trên SQLite QA, bao gồm scoped pending/invalid/confirmed, orphan history, global ID uniqueness, malformed IDs, non-finite source JSON và Unicode.
- Toàn suite SQLite sau tích hợp: **82 passed, 1 skipped**, 33.53 giây. Ca skipped là race test chỉ chạy với PostgreSQL riêng, không giả PASS ở SQLite.
- JUnit: `tests/results-sqlite-final-audit.xml`.
- Một warning upstream Starlette/TestClient dùng httpx hiện deprecated; test vẫn chạy đạt, không phải lỗi nghiệp vụ.

Root đang chịu trách nhiệm chạy lại toàn bộ trên PostgreSQL và browser acceptance; kết quả đó ghi riêng trong VERIFICATION.md, không suy từ SQLite.

## Kết luận

Không còn MAJOR/BLOCKER được reviewer phát hiện trong các phần đã đọc và các lỗi đã có hồi quy nêu trên tại thời điểm kiểm lại. Điều này không chứng nhận production Internet deployment hoặc toàn bộ Stage 02–08. Giới hạn local filesystem, parser không LLM/OCR và các phần chưa triển khai phải giữ công khai như DECISIONS.md/README.md.

Ghi chú nhỏ đã gửi root: CSRF header không phải ASCII nên trả 403 thay vì để compare_digest(str) phát TypeError. Đây không là bypass quyền; cần kiểm lại cùng các guard đầu vào khi root chạy lượt cuối.
