# Vòng sửa hiệu ứng, tải mở đầu và chữ

## Thay đổi sau khi đối chiếu mẫu

1. Dùng texture `mud_normal.webp` đúng URL trong manifest nguồn, lưu local và ghi hash trong `REFERENCE-3D-ASSETS.json`. Trường noise dùng cùng họ gradient tuần hoàn bốn octave với mã đã lưu; cố định seed để so sánh lặp lại được. Mẫu dùng seed ngẫu nhiên nên không tuyên bố khớp chính xác trường nhiễu của lần quay.
2. Shader hiện xử lý cả render cũ và mới thành đường nét độ sáng trong pha chuyển tiếp, ghép theo mask và phát sáng tại biên. Chuyển hero/Sidekick dùng vùng mở hướng tâm; các chương sau dùng wipe hữu cơ.
3. Snapshot camera nhúng giữ nguyên matrix thế giới. Bản cũ clone camera rồi tách parent có thể đổi góc nhìn của ảnh cũ.
4. Camera của chương mới có đoạn tự đi vào, thay vì giữ ở thời điểm chưa hoàn tất khi người dùng ngừng cuộn. Sidekick dùng mốc vào 1,133 của timeline nguồn; đây không phải giây video.
5. Clock camera/rig/mask chuyển từ nối tuyến tính sang nội suy cubic bảo toàn hình dạng, giữ key pose, không vượt biên và có vận tốc liên tục tại điểm nối. Idle có envelope vào mềm để tránh nhảy pose khi hết mở đầu.
   Rig có khoảng ổn định ngắn 1,6–1,7s tại pose đảo chiều, tránh chạm đỉnh giữa hai frame rồi quay lại ngay; mốc này là hiệu chỉnh theo đoạn ổn định nhìn thấy trong nguồn, không phải thời điểm xương gốc được khôi phục tuyệt đối.
6. Mép giấy thay polygon tĩnh bằng SVG turbulence/displacement; chỉ cập nhật khi mép ở gần viewport, reduced motion tắt biến dạng. Chữ và vùng đọc không bị dịch chuyển theo noise.

## Ba vòng so sánh

| Vòng | Quan sát từ bản ghi | Điều chỉnh tiếp |
| --- | --- | --- |
| 1 | Có pha đường nét; chân dung Sidekick còn quá sát và chữ hiện sớm | Tách clock đi vào camera; giảm chuyển cảnh 850 → 650ms; chữ vào sau |
| 2 | Camera/khung hình tốt hơn, nhưng chữ xuất hiện gần giữa thay vì lên từ thấp như mẫu | Tăng quãng chữ đi lên; cửa sổ vào chữ từ progress 0,35–0,95; theo cuộn để chữ rời khung |
| 3 | Có nét cũ nhường cho hình mới; tiêu đề xuất hiện thấp rồi ổn định, không bật sớm | Giữ bản này và kiểm tra toàn bộ scene, trạng thái tải, typography |

Bằng chứng trong `runtime/verification/effects-refinement/round-{1,2,3}`: clip thật và ảnh theo mốc 0,1s. `transition-comparison.jpg` đặt ảnh nguồn, vòng 1 và vòng 3 cạnh nhau. Crop và pose chưa đăng ký từng pixel; đây là so sánh trực quan, không phải điểm phần trăm giống.

## Sửa trường hợp người dùng thấy tối/đang tải

- Cảnh mở được mount ngay trong khi chờ kiểm tra phiên, thay spinner toàn trang. Chuyển từ kiểm tra phiên sang form đăng nhập giữ cùng component cảnh để không phát lại clock do đổi nhánh UI.
- Kiểm tra phiên có thời hạn 5s. Manifest và trạng thái nạp cảnh có thời hạn 6s, không giữ trang tối vô hạn.
- Trong lúc chuẩn bị, tranh preview được hiển thị thay vùng đen trống.
- Lỗi import/React, tạo WebGL, shader hoặc render chuyển sang ảnh dự phòng và form dùng được. Fallback được chốt, không bị callback ready muộn che mất form; canvas được dọn tài nguyên.
- Khi WebGL không khả dụng, ảnh dự phòng không có chuyển động xương tay chân. Đây là giới hạn thực tế, không được gọi ảnh tĩnh là đã chạy hiệu ứng đầy đủ.

`check_opening_loading.py` thử 5 trường hợp: bình thường, auth bị treo, manifest bị treo, model bị treo và không có WebGL. Tất cả hiển thị form; hai trường hợp đầu vẫn chạy scene, ba trường hợp lỗi dùng fallback. Browser không có pageerror trong các trường hợp kiểm tra. Dữ liệu và ảnh: `runtime/verification/opening-loading`.

## Sửa chữ và bố cục theo ảnh người dùng

- Chữ tên mục 16px desktop, 15px tablet; số 13px, tabular, cột cố định; hàng tối thiểu 32px.
- Mục lục cố định bên trái, căn giữa theo chiều cao và có giới hạn chiều cao; nội dung dành khoảng riêng, không đè mục lục hoặc form.
- Mỗi dòng xác định nền sáng/tối tại chính vị trí của dòng. Trên giấy/Developer dùng chữ tối; trên tranh tối dùng chữ sáng. Không đổi cả menu bằng một cờ ở giữa viewport.
- Header cũng xác định nền ở vị trí riêng, tránh chữ tối trên tranh khi lớp kem mới lên nửa màn hình.
- Nhãn form 16px, input 17px, nút 16px, ghi chú 12px. Trên mobile, mục lục bên trái ẩn để không đè form; vẫn cuộn được qua các chương.

`check_index_typography.py` đạt ở 1440/970/768/390px: cỡ chữ, căn số, nền hỗn hợp, tương phản dòng đang chọn, header, không chồng form và không tràn ngang. Ảnh chứng cứ: `runtime/verification/typography-repair`.

## Kiểm tra đã chạy

- Build production và TypeScript đạt.
- `check_reference_clock.mjs`: giữ key pose, đơn điệu, không overshoot, vận tốc liên tục tại các điểm nối.
- Ghi hình vòng 1/2/3: đúng texture local, có frame trung gian, không lỗi page/shader.
- `check_paper_edge.py`: noise thay đổi theo thời gian, tọa độ vùng đọc ổn định, reduced motion dùng mép tĩnh.
- `check_all_cinema_scenes.py`: 13 scene đều ready, không pageerror sau thay đổi camera/transition.
- Kiểm tra bố cục nguồn và các trường hợp tải nêu trên đạt.

## Giới hạn còn lại

Các thành phần được sửa đã gần cơ chế nguồn hơn, đặc biệt pha đường nét và nhịp xuất hiện chữ. Chưa khẳng định khớp tuyệt đối camera, màu/ánh sáng, mọi khớp người và texture của bản quay. Form, copy và thẻ thông tin vẫn là thích nghi Video OS. Không dùng test chức năng hoặc số vòng chạy làm bằng chứng giống 100%.
