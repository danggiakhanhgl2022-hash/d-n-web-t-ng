# Bản dựng 3D theo video tham chiếu

Ngày cập nhật: 08/11/2026. Chỉ triển khai cục bộ.

## Điều chỉnh luồng đăng nhập và chuyển trang

Theo yêu cầu mới, biểu mẫu đăng nhập nằm chính giữa cảnh 3D mở đầu và có hoạt ảnh xuất hiện riêng. Phần cuộn bên dưới giới thiệu không gian làm việc cho editor video: ý tưởng, brief sáng tạo, tư liệu, phong cách, âm thanh, phiên bản, phản hồi và bàn giao hồ sơ. Nội dung này mô tả việc chuẩn bị cho biên tập; không tuyên bố đã có công cụ cắt dựng video trong trình duyệt.

Sau đăng nhập, mở khu vực dự án trực tiếp. Không lặp chuỗi 13 cảnh trên màn hình tổng quan. Một lớp chuyển cảnh không chặn thao tác chạy khi đăng nhập, đổi dự án, đổi mục hoặc đổi bước câu hỏi; nội dung mới xuất hiện trong 650 ms và lớp chuyển cảnh rút hết trong 850 ms. Tôn trọng tùy chọn giảm chuyển động của hệ điều hành.

`scripts/browser_check.py` đã bổ sung phép đo khung đăng nhập nằm giữa theo cả hai chiều, kiểm tra không còn phần giới thiệu sau đăng nhập, và kiểm tra animation chuyển trang thực sự chạy rồi trở về opacity 0. Chạy qua `scripts/verify_browser.py` trên database QA riêng.

## Thay đổi

Bản ảnh tĩnh/parallax trước đây đã được thay trên màn hình mở đầu và tổng quan bằng một chuỗi 13 cảnh WebGL. Dùng Three.js, GLTF/Draco, KTX2 và các mô hình, texture, timeline công khai của Shopify Editions Winter 2026. Mã dựng cảnh được viết trong dự án; không nhúng nguyên website, không chạy mã quảng cáo của website gốc.

Thứ tự cảnh: Hero → Sidekick → Agentic → Online → Retail → Marketing → Checkout → Operations → Shop app → B2B → Finance → Shipping → Developer. Mỗi cảnh có camera lấy từ keyframe, chuyển động GLB hoặc lớp video theo cuộn. Camera nhúng của cảnh Retail được dùng theo cấu hình nguồn. Có bloom, hạt sáng và chuyển cảnh mở từ tâm. Khung mở đầu, mục lục bên trái, tiêu đề lớn và các phần nền giấy nối tiếp nhau.

Tài nguyên lưu trong `frontend/public/renaissance/3d`; nguồn trong `REFERENCE-3D-ASSETS.json`. 66 tài nguyên tham chiếu khoảng 38,2 MB, cộng bộ giải mã đi kèm Three.js. Tải cảnh hiện tại và cảnh kế tiếp; giải phóng hình học/vật liệu của các cảnh xa. Giữ nút “Vào dự án” để đến biểu mẫu. Nội dung và các nhãn chương được đổi sang nghiệp vụ Video OS.

## Kiểm tra

- `npm.cmd run build`: biên dịch và TypeScript.
- `scripts/check_cinema.py`: mở Chrome, chờ mỗi cảnh thực sự `ready`, kiểm tra đúng mã cảnh và hai thời điểm timeline khác nhau của cả 13 cảnh; chụp ảnh từng cảnh.
- Kiểm tra nút vào biểu mẫu và bố cục rộng 390 px không tràn ngang.
- Báo cáo thực tế và ảnh: `runtime/browser-qa/cinema/`.
- Backend và dữ liệu khách hàng không bị chỉnh sửa. Các bài kiểm tra nghiệp vụ trước đó không được xem là đã chạy lại trong thay đổi giao diện này.

## Giới hạn phải công bố

Không có kết quả đo chứng minh giống 100% từng khung hình. Video người dùng quay màn hình laptop với phối cảnh, thao tác cuộn và tốc độ riêng. Bộ dựng hiện tại dùng cùng tài nguyên và timeline, nhưng ánh sáng, shader chuyển cảnh, quy đổi khoảng cuộn, nội dung nền giấy và chữ đã được dựng lại cho Video OS. Các mục này chưa được xác nhận trùng tuyệt đối với website gốc. Chuyển cảnh mở từ tâm là shader viết trong dự án, không phải shader gốc đã được đối chiếu từng tham số.

Khi không có WebGL hoặc tài nguyên thất bại, giao diện hiển thị ảnh dự phòng có thông báo. Khi hệ điều hành yêu cầu giảm chuyển động, giữ tư thế camera tĩnh và bỏ chuyển tiếp động; không gọi chế độ này là lỗi hoạt ảnh.

Không được dùng việc 13 cảnh tải thành công làm bằng chứng “giống 100%”. Đây là kiểm tra chức năng dựng cảnh, không phải đánh giá độ giống hình ảnh.
