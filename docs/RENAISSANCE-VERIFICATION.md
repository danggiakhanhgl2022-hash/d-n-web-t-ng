# Giao diện theo video tham chiếu — kiểm chứng

Ngày: 08/11/2026, Asia/Bangkok.

Người dùng đã chọn áp dụng phong cách video cho toàn bộ giao diện. Đã triển khai ở login, tổng quan dự án, bộ câu hỏi, tài liệu nguồn, review, lịch sử và các hộp thoại. Login/tổng quan có các chương cuộn kể chuyện; bảng và ô nhập giữ màu kem để đọc rõ trên nền tranh tối.

## Thay đổi thực tế

- Component `frontend/app/RenaissanceExperience.tsx`: nền theo ngữ cảnh, chuyển lớp ảnh, parallax con trỏ/cuộn, thanh tiến độ cuộn, hero và ba chương giới thiệu đúng năng lực chặng A.
- Theme `frontend/app/renaissance.css`: tranh Phục Hưng, chữ sáng, tiêu đề lớn, điều hướng cố định, nét viền mảnh, điểm nhấn hồng; lớp nội dung nền kem, responsive và reduced-motion.
- Cập nhật `page.tsx` và `layout.tsx` để dùng theme cho toàn ứng dụng, không chỉ trang giới thiệu.
- Bảy ảnh cục bộ lấy từ nguồn tham chiếu; URL/hash trong `REFERENCE-ASSETS.json`. Runtime không cần tải ảnh từ website gốc.
- Không thay backend, dữ liệu khách, quyền xác nhận hay gate; không mở thêm stage 02–08 bằng hình thức giao diện.

## Kiểm đã chạy

1. `npm.cmd --prefix frontend run typecheck`: PASS.
2. `npm.cmd --prefix frontend run build`: PASS, sau lần chỉnh animation cuối.
3. `scripts/verify_browser.py`: PASS cả 9 nhóm kiểm. Ngoài luồng nghiệp vụ cũ còn kiểm ô nhập/placeholder đạt tương phản tối thiểu 4.5:1, chữ nhập >=16px, câu hỏi >=20px.
4. Kiểm mobile 390px không tràn ngang; không có page runtime error.
5. Đã xem ảnh login, câu hỏi và review sau đổi theme. Kết quả/ảnh tại `runtime/browser-qa/`; dữ liệu và quyết định trong ảnh chỉ thuộc DB QA riêng.

## Phạm vi độ giống

Khớp hướng hình ảnh, nguồn tranh, bố cục editorial, mục lục, chuyển chương và cách dùng màu nhìn thấy trong video. Bản hiện tại dùng ảnh fallback, CSS parallax/crossfade và chuyển động theo cuộn. Chưa tái tạo mô hình/scene/camera WebGL 3D gốc và không có cơ sở tuyên bố giống 100% từng pixel hoặc toàn bộ tương tác Shopify.

Các chức năng trong Video OS vẫn theo dự án thực; nội dung Shopify và tính năng chưa triển khai không được nhận là tính năng của ứng dụng. Triển khai vẫn cục bộ tại `http://127.0.0.1:3100`.
