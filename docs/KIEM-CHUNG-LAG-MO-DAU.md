# Kiểm chứng cảnh mở đầu bị giật

Đã chạy Chrome headless tại 1366×768, ba lượt với browser context mới cho mỗi bản. Không ghi video đồng thời để tránh tải phụ ảnh hưởng phép đo. Context mới không có nghĩa cache GPU/hệ điều hành hoàn toàn lạnh. Không dùng rAF làm FPS xuất hình của GPU.

## Nguyên nhân xác nhận

- Camera/rig lấy tiến độ mở màn từ React state chỉ cập nhật khi thay đổi ít nhất 0,02. Intro dài 3,2×2,2=7,04 giây tạo các nấc khoảng 141 ms. Đo trước sửa cho trung vị khoảng 151 ms giữa hai thay đổi camera.
- Máy chủ được launcher trỏ qua `runtime/frontend-build.json`, trong khi `npm run build` trực tiếp ghi thư mục mặc định khác. Các lượt kiểm trước đó vẫn phục vụ bundle cũ `2dqygmuav_0gl.js`. Vì vậy không được dùng các kết quả đó làm bằng chứng bản sửa đã chạy.

## Bản đang chạy

Launcher đã dựng và chuyển sang `.next-build-c9ed187a14bf`; kiểm thực tế qua resource trình duyệt thấy bundle `2h9vtxphuh700.js`. Camera lấy thời gian trực tiếp từ render loop, không chờ nấc React; các tối ưu tải và hoạt ảnh đã viết trước đó cũng được đưa vào đúng bản phục vụ.

| Lượt | Trung vị cập nhật camera trước | Sau | P95 sau | Khoảng cập nhật camera >100ms sau |
| --- | ---: | ---: | ---: | ---: |
| 1 | 151,6 ms | 18,2 ms | 66,8 ms | 4 |
| 2 | 151,5 ms | 18,1 ms | 42,4 ms | 0 |
| 3 | 151,6 ms | 18,1 ms | 48,4 ms | 0 |

Chỉ tính các lần `canvas.dataset.timeline` thay đổi trong cửa sổ mở màn được script xác định. Đây là nhịp cập nhật trạng thái camera quan sát từ DOM; không phải phép đo trực tiếp GPU trình bày frame và không dùng nó để tuyên bố chất lượng hình ảnh giống nguồn.

Kết luận: đã xác nhận và khắc phục phần chuyển động bị chia nấc. Chưa được ghi “hết lag”: lượt đầu còn 4 khoảng cập nhật camera vượt 100ms; cả các lượt sau vẫn có long task khi tải/khởi tạo. Cần đánh giá thêm trên máy thực nếu còn giật ở tải lần đầu. Không có lỗi JavaScript ở cả ba lượt sau. Build và phép kiểm nội suy timeline đạt.

## Bằng chứng tái lập

- Script: `scripts/verify_opening_smoothness.py`.
- Trước: `runtime/verification/opening-performance/before-clock-fix.json`.
- Lượt đặt tên `after-clock-fix.json` thực ra vẫn dùng bản cũ: không dùng làm kết quả sau sửa.
- Sau đúng bản đang phục vụ: `runtime/verification/opening-performance/after-active-build.json` (có mã build và bundle mỗi lượt).
- Khi cập nhật lần sau dùng pipeline `manage.build_frontend()`/`manage.py update` để chuyển con trỏ bản dựng; không giả định build mặc định là bản launcher đang chạy.
