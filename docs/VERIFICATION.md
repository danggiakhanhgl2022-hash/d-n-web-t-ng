# Kết quả triển khai và kiểm chứng chặng A

Ngày hoàn tất kiểm tra: 08/11/2026, Asia/Bangkok.

## Kết quả bàn giao

Stage 01 đã có bản chạy cục bộ với Next.js/TypeScript, FastAPI/SQLAlchemy và PostgreSQL 17.11. Giao diện tại http://127.0.0.1:3100; backend tại http://127.0.0.1:8100. Migration hiện tại: `0001_stage01`. Hai dịch vụ được launcher quản lý, chỉ lắng nghe trên loopback.

Luồng hoạt động: đăng nhập → tạo dự án → bộ câu hỏi 16 CORE/35 câu nhánh → lưu nguồn/bằng chứng và gợi ý → phát hiện thiếu/mâu thuẫn/tư vấn → PM/Admin xác nhận → gửi review → quyết định cho snapshot/hash → xuất hồ sơ và handoff có điều kiện. Sửa nội dung sau duyệt làm stale và khóa handoff. Lịch sử câu trả lời, snapshot và approval cũ được giữ.

Đây là hoàn tất lát cắt phần mềm cục bộ của chặng A; không phải một Folder Thông Tin khách hàng đã được điền/duyệt thay người dùng. Lúc kiểm DB dùng thật: 1 owner, 0 dự án khách, 0 approvals. Các approvals trong kiểm thử chỉ thuộc DB/tenant QA riêng.

## Kiểm đã chạy thật

| Kiểm | Kết quả | Bằng chứng |
| --- | --- | --- |
| PostgreSQL integration toàn bộ suite tại thời điểm chạy | **84 passed**, 0 failed/0 skipped, 45.832 giây | [JUnit](../runtime/verification/postgres-tests.xml), [log](../runtime/verification/postgres-tests.log) |
| SQLite suite sau final audit | **82 passed, 1 skipped**; ca skip yêu cầu PostgreSQL thật | [JUnit](../tests/results-sqlite-final-audit.xml) |
| CSRF header ngoài ASCII sau bổ sung guard | **1 passed**, trả 403 thay vì lỗi 500 | tests/test_csrf_header.py; đồng thời có trong lượt PostgreSQL 84 ca |
| Xuất DOCX/PDF với câu trộn Việt/Nhật | **2 passed** bổ sung trên SQLite; nội dung Unicode đọc lại đúng, PDF có font nhúng | [JUnit](../runtime/verification/multilingual-tests.xml) |
| Browser acceptance Chrome | **PASS**, 8 nhóm kiểm và không có page runtime error | [kết quả](../runtime/browser-qa/result.json), [DB isolation](../runtime/browser-qa/isolation.json) |
| TypeScript | **PASS** `npm.cmd run typecheck` | frontend/tsconfig.json và nguồn hiện tại |
| Production build | **PASS** `npm.cmd run build` | frontend/.next/BUILD_ID |
| Dependency audit runtime frontend | **0 vulnerabilities** tại thời điểm kiểm | `npm.cmd audit --omit=dev --audit-level=high` |
| Launcher thực | **PASS** khởi động, kiểm lặp không tạo server trùng; HTTP frontend/API 200 | runtime/backend.log, runtime/frontend.log |

Hai ca đa ngôn ngữ được bổ sung sau lượt PG 84; không ghi thành 86 ca PostgreSQL đã chạy. Cảnh báo còn lại trong pytest là deprecation của Starlette/httpx TestClient; các assertions vẫn đạt.

## Browser acceptance đã thực hiện

1. Đăng nhập cookie session qua giao diện.
2. Tạo dự án và lưu câu trả lời từ form thật.
3. Upload nguồn TXT qua giao diện, chạy prefill, kiểm evidence và trạng thái chưa xác nhận.
4. Lưu các trường có cấu trúc mà không tự CONFIRMED; handoff vẫn khóa.
5. Tài khoản reviewer QA xác nhận, submit và duyệt đúng snapshot qua giao diện; handoff mở.
6. Tải ZIP/JSON/DOCX/PDF thật từ snapshot đã duyệt, kiểm chữ ký file/đọc nội dung.
7. Sửa sau duyệt: giữ lịch sử, trạng thái STALE và handoff đóng.
8. Kiểm mobile 390px không tràn ngang, không lỗi JavaScript.

Đã xem ảnh [login](../runtime/browser-qa/01-login.png), [bộ câu hỏi](../runtime/browser-qa/02-questionnaire.png), [review](../runtime/browser-qa/03-review.png), [đã duyệt QA](../runtime/browser-qa/04-approved.png), [mobile](../runtime/browser-qa/05-mobile.png). File hồ sơ có tên `qa-information-package.*` trong cùng thư mục là dữ liệu QA, không phải hồ sơ khách.

## Các lỗi quan trọng đã sửa

- Dữ liệu nháp sai kiểu không làm evaluator/branch trả 500; confirmation kiểm semantic riêng.
- Giá trị JSON không hữu hạn hoặc Unicode hỏng trong prefill không trở thành số JSON lỗi; văn bản tên riêng như Infinity được giữ như đề xuất chuỗi chưa xác nhận.
- Scoped CORE override của đầu ra hiện hành phải được xác nhận và đúng semantic, không bị gate bỏ qua.
- ID deliverable/variant phải duy nhất toàn ma trận. Scope đã gỡ trở thành lịch sử không áp dụng, không bị coi là yêu cầu đang hiệu lực.
- Snapshot export giữ nguyên payload/hash, nhưng metadata lịch sử cập nhật để không nhầm bản cũ là hiện hành.
- CSRF header Unicode trả 403; tenant/role/actor đều kiểm phía server.
- Source bytes có size/checksum thật, kiểm lại khi dùng; template câu hỏi được đóng băng cùng snapshot.
- Tải lại trang khôi phục dự án đang làm. Link tải bản được duyệt ràng buộc snapshot ID cho cả bốn định dạng.

## Phạm vi chưa bao gồm

Chặng B/stage 02–08, generation/AE/credits/delivery khách chưa triển khai. Prefill hiện là parser theo mã CORE-XX, không có LLM tự hiểu văn bản tự do hoặc OCR; tài liệu không trích được có fallback thủ công rõ ràng. File storage cục bộ, chưa triển khai S3/MinIO hay dịch vụ Internet. Quyết định duyệt khách/ngân sách thật luôn do người có quyền.

Xem [DECISIONS.md](DECISIONS.md), [STAGE01-SCOPE.md](STAGE01-SCOPE.md), [IMPLEMENTATION-CONTRACT.md](IMPLEMENTATION-CONTRACT.md) và [FINAL-AUDIT.md](FINAL-AUDIT.md) để đối chiếu phạm vi và nguồn kiểm.
