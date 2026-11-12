# Backend — Chặng A / Stage 01

FastAPI + SQLAlchemy, PostgreSQL cho môi trường thật; SQLite chỉ là lựa chọn test/cục bộ riêng. Không có tài khoản/mật khẩu mặc định hoặc dự án mẫu được tự phê duyệt.

Từ thư mục backend, đặt DATABASE_URL và STORAGE_DIR (launcher gốc đọc .env), rồi chạy:

```powershell
..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
..\.venv\Scripts\python.exe -m app.bootstrap --username owner --display-name "Người quản lý" --tenant-name "Studio"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8100
```

CLI hỏi mật khẩu qua getpass; automation dùng --password-stdin, không đưa mật khẩu vào argv hoặc log. Không chạy bootstrap lại để đổi mật khẩu/tài khoản cũ. ADMIN có thể tạo user cùng tenant bằng POST /api/v1/users; role PM được xác nhận/duyệt, ACCOUNT chỉ sửa, VIEWER chỉ đọc. Actor/tenant lấy từ server session, không tin trường reviewer_id bên client.

API docs: http://127.0.0.1:8100/docs. Health: /api/v1/health. Frontend dùng cùng origin qua Next rewrites; cookie HttpOnly/SameSite strict, mọi mutation xác thực cần X-CSRF-Token trả từ login/me. COOKIE_SECURE=true khi triển khai HTTPS. Rate limit login cục bộ 8 lần sai/5 phút theo IP+username; multi-instance deployment cần shared limiter.

create_app(database_url=None,storage_dir=None) trả app có state.engine/session_factory/storage_dir để dùng fixture test riêng. app.bootstrap.create_owner tạo tenant/admin chỉ theo yêu cầu trực tiếp, không tạo client project hay approvals.

51 câu hỏi versioned: 16 CORE + 35 câu theo nhánh. 16 câu cốt lõi phải hợp lệ và được PM/ADMIN xác nhận; các câu chuyên sâu hỗ trợ clarification đúng stage, không ép mọi câu hiện ra. Các trạng thái nháp giữ được dữ liệu chưa hoàn chỉnh; confirmation và Gate01 kiểm semantic. CORE16 PLANNED chỉ xác nhận kế hoạch có trách nhiệm, không cấp quyền generation hoặc bàn giao.

Prefill hiện là adapter trích theo marker CORE-XX: câu trả lời (JSON một dòng cho field cấu trúc) từ TXT/MD/DOCX/PDF có text; không gọi AI/LLM. Mọi kết quả chỉ PROPOSED_FROM_SOURCE; xung đột giữ giá trị cũ và ghi đề xuất mới vào audit. PDF scan/encrypted/ngoài giới hạn trả MANUAL_REQUIRED, không OCR giả. File gốc UUID lưu trong STORAGE_DIR, checksum kiểm lại khi sử dụng; chỉ nhận file10MB, PDF tối đa200trang để trích, DOCX có giới hạn giải nén. Không nhận URL remote, không có SSRF fetch.

Snapshot giữ canonical JSON và SHA256 cùng exact questionnaire_definition. Decision cần expected_revision/snapshot_id/content_hash và PM/ADMIN thật. Các thao tác nội dung tăng revision, làm snapshot cũ historical và chặn Stage02. Audit giữ before/after answer revisions; không có route sửa/xóa snapshot/approval/audit. Không ghi mật khẩu trong audit.

Package ZIP có INPUT/WORK/OUTPUT/REVIEW/APPROVAL/SNAPSHOT và manifest checksum thật. Payload/hash được ký duyệt trong JSON giữ nguyên; metadata bao ngoài historical/current_project_revision cập nhật đúng hiệu lực hiện hành, cùng header X-Snapshot-Status và GET project/stage02. DOCX/PDF xuất từ cùng payload có câu trả lời, ma trận, quyền, gaps và acceptance; ZIP bản cũ gắn nhãn HISTORICAL. PDF dùng fontUnicode từ PDF_FONT_PATH (ArialWindows/DejaVuLinux mặc định); Nhật cần PDF_CJK_FONT_PATH (MSGothicWindows mặc định) và font được embed; thiếu font báo503 thay vì file sai giả.

Phạm vi chưa gồm Stage02–08, media generation, chi credits, renderAE hoặc delivery khách hàng. UI hiển thị ranh giới này; Gate01 cho phép handoff không đồng nghĩa Stage02 đã được thi công.
