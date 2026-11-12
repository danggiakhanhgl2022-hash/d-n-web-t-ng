# Kết quả thực hiện hiệu ứng theo prompt

## Thay đổi có căn cứ

1. So ảnh mở nguồn tại khoảng 1,0–1,3s với bản web trước: nhân vật web lộ quá sớm. Đã kéo dài camera tiến tới bố cục cuối, giữ rig riêng. Ảnh web vòng gần cuối khoảng 1,0s chỉ lộ áo/tay ở hai bên thay vì cả mặt như trước. Ở 1,3s vẫn thấy nhân vật nhiều hơn mẫu; chưa xác nhận độ khớp chính xác do phối cảnh/timestamp. Ảnh trước: `runtime/verification/opening-before-current`; bản ghi sau: `runtime/verification/opening-005`.
2. Rà timeline và GLB: camera ở một số cảnh kết thúc trước các track đồ vật; giới hạn thời gian theo camera đã cắt ngắn phần animation sau. Các cảnh cần đủ thời lượng được lấy theo sequence, còn Sidekick tách thời gian camera/visibility khỏi thời gian bốn clip vòng. Một thử nghiệm đầu làm nhân vật biến mất quá sớm; đã phát hiện qua ảnh, sửa tách thời gian và xem lại ảnh có nhân vật tại 25% và 50% quãng scene.
3. Tên clip tay/bút trong GLB dùng dấu chấm, còn khóa trong timeline dùng dấu gạch dưới. Đã ghép được hai dạng và phát clip loop có cấu hình loop trong khi dừng cuộn; reduced motion giữ nguyên chế độ giảm chuyển động. Nhịp loop là cách dùng clip và cấu hình có sẵn, chưa chứng minh phục hồi chính xác tốc độ nguồn.
4. Vòng Sidekick quá tối do cảnh local không có environment map; chỉ giảm metallic của các mesh vòng. Vỏ/đáy hub Retail cũng được nâng sáng nhẹ để thấy mép/cổng; đây là hiệu chỉnh có chủ đích, chưa trùng màu/ánh sáng video quay.
5. Giữ logic chuyển scene tải chậm: canvas cũ vẫn thấy, chuyển động không nhảy hết khi frame render chậm. Form vẫn tự hiện sau intro cho người chưa đăng nhập.

## Đối chiếu và kiểm thử

- Đã xem frame nguồn/các bảng 0,05s trước đó, xem lại ảnh web mở đầu, ảnh Sidekick 25%/50% và Retail 25%/50%. Các ảnh khác tỷ lệ, phối cảnh và trạng thái cuộn; chưa đo pixel chuẩn hóa.
- `check_object_motion.py`: bốn clip vòng thay đổi khi cuộn; clip sách Agentic và hub Retail có thời gian thay đổi khi cuộn; tay và bút Online đổi thời gian clip khi dừng cuộn; không pageerror. Test khẳng định tiến trình clip thay đổi, không chứng minh mọi chi tiết chuyển động thấy rõ hoặc giống video.
- `check_all_cinema_scenes.py`: chạy lại sau lần sửa cuối, 13 scene ready, từng scene sau hero có mẫu chuyển trung gian, không pageerror.
- `check_slow_scene_transition.py`: scene trước còn thấy khi asset scene sau chậm, scene sau có pha trung gian.
- Build/TypeScript, clock, mở đầu và form/login giả lập ở 1440/970/390 đạt. Kiểm tra xóa bằng API giả lập ở vòng giao diện trước đạt; không thao tác xóa dữ liệu thật.
- `record_motion_walkthrough.py` tạo bản ghi cuộn mô phỏng theo mốc và tự đóng form trong bài audit; đây không phải thao tác gốc trong video.
- Đã cập nhật bản ghi mở đầu 0,01s và bản cuộn mô phỏng sau lần sửa cuối; bản cuộn thu được 3395 frame và thấy đủ 13 scene. Timestamp thực vẫn cần được kiểm tra khi chọn frame đối chiếu.

## Chưa đạt / cần làm tiếp

- Không kết luận khớp 100%: vùng sáng/màu, crop camera và tư thế tại khoảng 1,3s còn khác. Cần bản ghi đủ frame khoảng 0,676–0,957s và căn phối cảnh màn laptop trước khi đo.
- Chưa chứng minh điện thoại, thẻ ứng dụng, bút hoặc việc tách/lắp hub khớp từng frame. Thời gian clip thay đổi không chứng minh chi tiết được nhìn thấy hoặc đúng quỹ đạo. Nội dung trung gian/Tinker, typography và UI khác bản mẫu còn cần so từng trạng thái cuộn.
- Thiết bị lỗi WebGL dùng ảnh dự phòng, không có rig 3D. Không khẳng định chạy được hiệu ứng 3D trên mọi thiết bị.
- Các test UI dùng auth/API giả lập; không kiểm tra đăng nhập bằng tài khoản thực. Trong test mô phỏng request treo, Playwright có cảnh báo `CancelledError` ở bước cleanup dù các case đã trả kết quả; không nhầm cảnh báo harness với lỗi trang.
