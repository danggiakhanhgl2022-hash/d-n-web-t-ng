# Quyết định triển khai chặng A

Ngày: 07/11/2026, Asia/Bangkok.

1. Phạm vi: chỉ Stage 01 của dự án V3. Chặng B hiển thị khóa; chỉ có kiểm tra điều kiện handoff, chưa có tạo video/AE/generation.
2. Triển khai trong ai-video-production-os/, giữ nguyên 157 file mẫu V2.2. Dữ liệu chạy thật tách khỏi dữ liệu test và tài liệu nguồn.
3. Next.js/TypeScript và FastAPI/SQLAlchemy; PostgreSQL 17 cục bộ trên 127.0.0.1:54329. Image PostgreSQL được pin bằng digest. SQLite chỉ dùng cho test nhanh hoặc chế độ phát triển được chọn rõ; không được dùng kết quả SQLite để nhận đã kiểm PostgreSQL.
4. Lưu file gốc bằng filesystem adapter cục bộ với UUID, kiểm tenant qua API và checksum. Object storage S3/MinIO, hàng đợi và worker media chưa cần để chạy tiếp nhận đồng bộ; chưa được triển khai trong lát cắt này. Cần adapter storage và chính sách backup khi triển khai nhiều máy.
5. Không có khóa/provider AI được cung cấp. Prefill hiện là parser xác định từ các dòng CORE-XX: có evidence, hỗ trợ JSON cho trường có cấu trúc; không gọi LLM và không gọi nó là hiểu ngữ nghĩa AI. Văn bản tự do vẫn đọc được và người dùng ánh xạ thủ công. Không tự xác nhận đề xuất.
6. PDF scan hoặc tài liệu không trích được được ghi rõ cần nhập/đối chiếu thủ công. Không giả kết quả OCR. Chỉ đọc TXT/MD/DOCX/PDF, giới hạn dung lượng và kiểm archive DOCX; không chạy macro hoặc lệnh trong file.
7. Quyền ADMIN/PM xác nhận và duyệt; ACCOUNT nhập; VIEWER đọc. Actor/tenant do session phía backend xác định. Không mặc định tài khoản/password chung; owner cục bộ được bootstrap với mật khẩu ngẫu nhiên riêng.
8. Stage 01 yêu cầu xác nhận đầy đủ 16 câu lõi với dữ liệu đúng kiểu/nghĩa. Nhánh chuyên sâu hiển thị thích ứng; các chi tiết chỉ cần trước sản xuất không chặn intake chỉ vì chưa có ứng viên media. Xung đột/cần tư vấn chưa xử lý phải hiện rõ và chặn khi tác động gate.
9. Snapshot là canonical JSON bất biến, có SHA-256; approval event riêng trỏ hash. Feedback và lịch sử giữ riêng; mọi thay đổi có ảnh hưởng nội dung làm stale/hủy hiệu lực handoff bản hiện hành, không viết lại snapshot cũ.
10. Kiểm thử dùng tenant/DB riêng có nhãn QA, có thể thực hiện confirmation/approval fixture. Không có dự án khách thật nào được agent xác nhận hoặc duyệt thay người dùng.
11. Phục vụ qua loopback, cookie HttpOnly/SameSite và CSRF. Chưa là dịch vụ Internet: cần HTTPS, reverse proxy, secret management, backup và kiểm bảo mật/vận hành trước khi mở mạng.

Tài liệu kỹ thuật tham khảo: [FastAPI SQL databases](https://fastapi.tiangolo.com/tutorial/sql-databases/), [Next.js rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites). Các dependency thực cài được pin trong requirements.lock.txt và frontend/package-lock.json.
