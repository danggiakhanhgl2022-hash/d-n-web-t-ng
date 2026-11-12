# Bóc tách nhân vật và đồ vật theo mô hình hiện có

Đây là kiểm kê cấu trúc tài nguyên thật, không phải kết luận các phần đã được tạo lại hoặc khớp từng khung hình. Chạy `scripts/inventory_cinema_parts.py` để tạo danh sách đầy đủ tại `runtime/verification/cinema-parts-inventory.json`. Tên mesh và quan hệ cha/con lấy từ GLB; chuyển động xương có thể tác động lên mesh dù mesh không trực tiếp là đích của kênh animation.

## Mở đầu

- Nền phong cảnh là một lớp ảnh KTX2. Vùng sáng và biên tan là shader; camera, shader và tư thế nhân vật có đồng hồ riêng.
- Mô hình Hero có 15 mesh, hai nhánh `Robed Woman Rig` và `Robed Man Rig`, một clip `Scene` gồm 552 kênh. Nhân vật nữ có thân/áo, đầu, hai tay, dây giày, ván trượt và cốc; nhân vật nam có thân/áo, đầu, hai tay và hai mesh túi hồng. Mỗi phần có liên kết xương và thứ bậc riêng.
- Các phần thân và áo trong mesh liền không thể xem như từng mảnh độc lập chỉ bằng cách đổi tên node. Tách vật lý phải giữ trọng số da, xương và thứ bậc; tách clip cũng phải xử lý tên xương trùng và không làm thay đổi tư thế gốc.
- Mốc tham khảo từ video: vệt sáng đầu khoảng 0,167s, mở dần 0,25–0,8s, tay áo phải khoảng 0,867s, hai người lộ dần khoảng 1–1,8s. Các giá trị này là thời điểm trong bản quay 30 fps, không phải thông số hoạt hình gốc.
- Thử chỉnh riêng đồng hồ camera và rig để chậm lộ nhân vật ở 1,3s. Ảnh chụp mới vẫn khác video: mặt nhân vật nam còn lộ sớm, tỷ lệ/crop và vị trí tay còn khác. Chưa có căn chỉnh phối cảnh màn hình nguồn nên không công bố phần trăm khớp.

## Các cảnh tiếp theo

- Sidekick: mô hình chính 7 mesh, 5 clip, nền sao riêng; cần theo dõi chân dung, các vòng và máy tính độc lập khi so với mốc chuyển cảnh 5,95–7s.
- Agentic: tiền cảnh một mesh, sách có 7 mesh và một clip, cụm đạo cụ có 10 mesh và một clip, nền riêng. Chưa xác minh được một mesh điện thoại độc lập khớp ảnh quay.
- Online: mô hình 6 mesh, 4 clip, nền và lớp video riêng. Clip tay và bút đã có chuyển động; cần đối chiếu hướng, nhịp và lớp màn hình theo từng ảnh.
- Retail: môi trường 4 mesh, hub 7 mesh, tiền cảnh 13 mesh; mỗi mô hình có một clip và có lớp video riêng. Cần xác minh từng bộ phận hub tách/lắp và vị trí dưới bàn, không suy ra chỉ từ số mesh hoặc thời gian clip.
- Các cảnh còn lại cũng được liệt kê trong JSON, gồm cả ảnh nền/lớp video. Cần so từng cảnh và từng trạng thái cuộn trước khi kết luận đạt mẫu.

## Trạng thái công việc

Đã chia clip mở đầu 552 kênh thành 12 nhóm action theo nhánh: thân/rig nữ, hai tay nữ, ván, cốc, hai dây giày; thân/rig nam, hai tay nam và hai túi. Mỗi kênh vẫn dùng nguyên đường cong nguồn, bộ xương và mesh cũ. Phần đầu và các phần tay chân nằm trong mesh/nhánh thân không nhất thiết có kênh riêng; chưa tách hình học hay tạo chuyển động mới cho từng ngón tay, đầu hoặc mảnh áo. Các nhóm hiện chạy cùng thời điểm clip để giữ nguyên tư thế, chưa căn chỉnh thời gian từng nhóm độc lập theo video.

Kiểm tra `scripts/check_hero_parts.py` tạo hai bản sao bộ xương độc lập, phát clip gốc và các nhóm ghép ở bảy tư thế, so sánh thành phần vị trí, tỷ lệ và quaternion của mọi node. Đủ 552 kênh, không có kênh không tìm thấy node, và kết quả đạt ngưỡng sai khác `1e-6`. Kiểm tra này chỉ chứng minh ghép lại giống chuyển động của mô hình hiện có, không chứng minh giống video quay. Các cảnh Sidekick, Agentic, Online và Retail đã được kiểm tra đồng hồ chuyển động có thay đổi, nhưng chưa bóc tách và căn chỉnh toàn bộ từng vật so với video.

Chưa hoàn thành yêu cầu tách vật lý từng phần hay ghép và đối chiếu từng vật theo thời gian thực cho toàn bộ cảnh. Cần tách hình học có giữ trọng số da khi thật sự cần, xây dựng và hiệu chỉnh đồng hồ riêng cho từng nhóm dựa trên các khung video, rồi ghi lại và so sánh cùng góc nhìn; tránh coi các nhóm clip đang đồng bộ là hiệu ứng đã tái dựng chính xác.

## Lần tiếp tục: nhóm kênh của các cảnh còn lại

Đã áp dụng phân nhóm kênh theo node hoặc nhánh sở hữu xương cho các clip GLB còn lại, sau đó phát các nhóm cùng thời điểm với clip gốc. Ví dụ sách Agentic có sáu nhánh armature, đạo cụ Agentic có nhóm ván, bánh, giày, mũ và áo; Online có các nhóm canvas, người, tay và bút; hub Retail có nhóm nắp, đáy, bảng mạch và ốc, còn dây được nhóm theo nhánh xương của từng dây. Những mesh không có kênh độc lập vẫn đi theo node cha và không trở thành chuyển động độc lập chỉ vì được đặt tên trong kiểm kê.

`scripts/check_scene_parts.py` đã kiểm tra 13 cảnh, 36 clip và các nhóm của chúng: không mất kênh hoặc node đích; bản tách và clip gốc khớp thành phần biến đổi tại bảy tư thế lấy mẫu trên các bản sao. Cảnh Marketing không có clip GLB nên kết quả 0 clip không chứng minh có chuyển động đồ vật ở cảnh đó. Kết quả chi tiết: `runtime/verification/scene-parts/checks.json`. Đây là kiểm tra bảo toàn chuyển động sẵn có, không phải kiểm tra độ giống video hay chuyển động của toàn bộ mesh.

Đã xem lại ảnh web Retail tại vị trí kiểm thử 25% và bảng khung video khoảng 20–21 giây. Hai ảnh vẫn khác bố cục và góc máy; vị trí cuộn 25% chưa được chứng minh tương ứng thời điểm trong bản quay, nên không dùng chúng làm phép đo giống/khác định lượng. Chưa có ánh xạ đáng tin cậy giữa thời gian video và tiến độ cuộn, cũng chưa hoàn thành các đồng hồ riêng hoặc tái dựng vật thể không có trong tài nguyên.

## Lần tiếp tục: đối chiếu Retail và form đăng nhập

Đã ghi 10 mức cuộn Retail bằng `scripts/capture_retail_progress.py`, có lưu thời gian timeline và ảnh tại `runtime/verification/retail-progress/`; bản trước chỉnh nằm ở `runtime/verification/retail-progress-before/`. Đối chiếu bằng mắt cho thấy trình tự bàn, hộp dưới bàn và góc nhìn lên mái vòm có trong mô hình. Màu hộp trước đó quá tối do thiếu phản xạ môi trường, nên đã tăng sáng riêng hai vật liệu vỏ và đáy. Ở mức cuộn 40%, ảnh sau chỉnh cho thấy hộp màu xám và các cổng rõ hơn; vẫn không phải ánh sáng hay khung hình được khôi phục chính xác từ video. Vị trí cuộn không được gán nhầm thành giây của video.

Khi kiểm thử phát hiện nhánh đăng nhập hiện tại chưa bật `autoLogin`, làm form không tự mở sau intro. Đã bật lại tùy chọn này; kiểm thử độc lập xác nhận form xuất hiện, đóng/mở lại được và bố cục ở 1440/970/390. Một lượt kiểm thử trước đó hết thời gian vì form thực sự chưa được bật, không phải đã chứng minh do tải máy. Các bài sau sửa đều chạy đạt; kiểm thử đăng nhập dùng tài khoản/API giả lập.

## Lần tiếp tục: Hero sang Sidekick

Đã xem lại bảng khung 6,0–7,0s của video và ghi chuyển cảnh web trước/sau bằng `scripts/record_scene_transition.py`. Ở video có lóe sáng gần giữa, vùng tối với biên hạt mở rộng, sau đó mới lộ chân dung; bản web trước chỉnh mở lệch sang phải và viền chân dung xuất hiện sớm. Bản mới đưa tâm chuyển cảnh về gần giữa, thêm lóe sáng ngắn, giữ màu ngoài biên lâu hơn và giảm nét chân dung ở pha đầu. Chữ cảnh mới cũng được cho xuất hiện theo tiến độ chuyển cảnh, thay vì hiển thị ngay trên vệt sáng.

Ảnh và thời điểm chụp thực ở `runtime/verification/effects-refinement/sidekick-before-20261111/` và `sidekick-final-20261111/`. Mốc thời gian bản web là thời gian ước lượng từ tiến độ transition và CDP, không phải đồng hồ cuộn video gốc. Ảnh sau chỉnh cho thấy đốm sáng và vùng tối ở giữa, nhưng biên hạt còn mang dạng vòng tương đối đều; kích thước, mật độ hạt, chân dung và phối cảnh chưa được chứng minh khớp mẫu. Kiểm thử build, chuyển cảnh qua các pha, tải cảnh chậm, mở đầu, reduced motion và tự mở/đóng form đạt; không có lỗi shader được phát hiện trong bài ghi.

## Lần tiếp tục: vòng Sidekick và quãng cuộn

Đã nâng sáng nhẹ vật liệu vòng la bàn và bổ sung dao động chậm bằng clip vòng sẵn có khi dừng cuộn. Chuyển động này giảm dần khi cuộn và không chạy trong chế độ giảm chuyển động; nhịp dao động là thiết kế bổ sung, chưa đo được chính xác từ video. `scripts/check_sidekick_idle.py` kiểm tra thời gian clip và quaternion của node vòng thay đổi khi dừng, rồi giữ nguyên ở chế độ giảm chuyển động. Ảnh và số đo được lưu tại `runtime/verification/sidekick-idle/`.

Trong lúc kiểm tra phát hiện `.cinema-scene-space` thiếu chiều cao vì stylesheet cũ không còn được nạp, khiến các bài kiểm thử nhảy tới các mức cuộn khác nhau thực ra vẫn ở gần đầu cảnh. Đã khôi phục chiều cao theo quãng cuộn từng cảnh và tỷ lệ di động. Sau sửa, `check_object_motion.py` chạy lại đạt: vòng, sách và hub thay đổi theo cuộn, clip tay/bút có tiến triển khi dừng. Một lần khởi động lại gặp khóa tệp build trên Windows; build lại và khởi động sau đó thành công. Việc đồng hồ và quaternion thay đổi chưa xác nhận kích thước, tốc độ hoặc phối cảnh khớp video gốc.

## Lần tiếp tục: giấy xé ở Online

Đối chiếu các khung 14,0–14,45s cho thấy mép giấy đi từ dưới lên trước người vẽ. Đã khôi phục mép giấy dùng SVG displacement và bố cục nội dung theo luồng, để nội dung giấy không tràn lên chương kế tiếp. Camera Online được giữ ở tư thế trước khi rời nhân vật trong lúc giấy che lên; lớp video vẫn theo tiến độ cuộn. Đây là điều chỉnh theo quan sát, chưa phải xác nhận khớp từng frame hoặc khôi phục được thao tác cuộn gốc.

`scripts/check_online_paper.py` lưu ảnh ở ba vị trí của mép giấy tại `runtime/verification/online-paper/`, xác nhận bộ lọc và chế độ giảm chuyển động. Ảnh 65% cho thấy người vẽ ở phía trên mép giấy; 13 cảnh hiển thị không pageerror, kiểm thử chuyển động đồ vật và bố cục đăng nhập ở ba kích thước đạt.
