# Hợp đồng lát cắt Stage 01

| Mục | Quy định triển khai |
| --- | --- |
| 1. Mục tiêu | Nhận yêu cầu → câu hỏi/nguồn → xác nhận → Folder Thông Tin → Gate 01/snapshot |
| 2. Nguồn đầu vào | Người dùng đăng nhập, câu trả lời, TXT/MD/DOCX/PDF khách gửi |
| 3. Schema đầu vào | Questionnaire template versioned, CORE01..16 và nhánh, expected_revision, source/evidence |
| 4. Điều kiện trước | Session hợp lệ, đúng tenant/role, schema hợp lệ; đăng ký intake không đòi brief đủ |
| 5. Xử lý | Lưu draft → xác định branch → kiểm thiếu/mâu thuẫn → confirm đúng quyền → review/feedback → submit → quyết định |
| 6. Đầu ra | Canonical intake contract, folder ZIP, JSON/DOCX/PDF, review/checklist, snapshot/hash/approval và audit |
| 7. Trạng thái | DRAFT/WAITING hoặc review/changes/rejected/approved/stale theo backend; trạng thái answer riêng |
| 8. Lỗi | 401 session, 403 quyền/CSRF, 404 tenant/resource, 409 revision/hash/stale, 422 dữ liệu, lỗi parsing/upload rõ ràng |
| 9. Khả dụng | Local PostgreSQL/filesystem; parser xác định, không LLM/OCR/provider/AE |
| 10. Quyền | ADMIN quản trị; PM/ADMIN confirm/duyệt; ACCOUNT chỉnh; VIEWER chỉ đọc |
| 11. Truy vết | Answer/source/revision/actor → snapshot/hash → approval/handoff; export không sửa canonical dữ liệu |
| 12. API | Xem IMPLEMENTATION-CONTRACT.md và /docs của backend chạy cục bộ |
| 13. Giao diện | Dashboard → câu hỏi theo nhóm → nguồn → xem xét/duyệt → snapshot/download/lịch sử |
| 14. Kiểm thử | API integration SQLite, PostgreSQL riêng, browser E2E, kiểm file ZIP/DOCX/PDF và snapshot/hash |
| 15. Hoàn tất | Các kiểm quan trọng chạy đạt; app chạy được; không giả dữ liệu khách, không mở Stage02 khi chưa duyệt hoặc stale |

Chi tiết kết quả thực chạy sẽ được ghi trong VERIFICATION.md. Tài liệu này mô tả phạm vi, không tự chứng minh đã kiểm đạt.
