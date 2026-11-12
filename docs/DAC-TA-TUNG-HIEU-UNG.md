# Đặc tả từng hiệu ứng trong video

> Trạng thái “bản hiện tại” dưới đây là baseline tại lúc phân tích. Các vòng sửa tiếp theo đã thêm texture mud nguồn, pha đường nét, clock mềm, camera vào cảnh và mép giấy động; xem `EFFECTS-REFINEMENT-2026-11-10.md` để biết thay đổi, bản ghi so sánh và kiểm tra mới.

Phân tích ngày 10/11/2026, dựa trên ảnh nguồn 0,1s, ảnh quay nguyên khung và mã/asset gốc đã lưu. Đây là hồ sơ phân tích, không phải xác nhận bản web đã khớp toàn bộ.

Ký hiệu: **thấy** = quan sát trong video; **xác nhận** = có cơ chế tương ứng trong mã/asset; **cần đo** = chưa xác định chính xác thông số hoặc quan hệ với thời gian video. Các mốc dưới đây là giây trong bản quay. Ranh giới được xác định theo bước 0,1s nên không được coi là chính xác hơn độ phân giải đó.

## FX01 — Vùng tranh xuất hiện từ nền tối

**Thấy:** 0,0–0,1s phần lớn tối; khoảng 0,2s bắt đầu có mảng tranh nhỏ. Vùng đó lớn nhanh trong 0,3–0,7s, rồi tiến ra rìa trong khoảng tiếp theo.

**Diễn biến:** có vùng chưa hiện, vùng đang chuyển và vùng đã hiện. Chi tiết tranh trong vùng đã mở được giữ lại; không phải toàn bộ ảnh tăng độ sáng đồng thời. Tâm mở gần giữa, nhưng biên không đối xứng.

**Xác nhận:** shader gốc có khoảng cách tới tâm, bù aspect màn hình, trường ngưỡng theo trục ngang và phần nhiễu làm lệch ngưỡng. Tâm có thể được chiếu từ không gian 3D và pha một phần ảnh hưởng con trỏ.

**Cần đo:** quỹ đạo tâm sau khi nắn phối cảnh; diện tích vùng đã mở theo từng frame; thời điểm vùng mở thật sự chạm từng cạnh. Crop cố định của laptop chưa đủ cho phép đo chính xác các đại lượng này.

**Nghiệm thu:** chồng các biên tại 0,2/0,4/0,6/0,8/1,0s sau khi căn viewport; so tâm, diện tích và phần lõm/lồi. Hai biên cùng bán kính nhưng khác hình dạng vẫn chưa đạt.

**Bản hiện tại:** đã có mask hiện tranh, nhưng trường nhiễu và đường cong tăng trưởng là tái dựng.

## FX02 — Mép tranh gồ ghề và biến dạng

**Thấy:** biên có mảng lớn lồi/lõm, xen những đoạn nhỏ rách và loang. Có lúc mảng dường như tách hoặc xoắn; hướng biến dạng không lặp đều quanh vòng.

**Xác nhận:** nguồn kết hợp texture mud normal và noise thay đổi theo thời gian. Những trường này làm lệch điểm mà một pixel chuyển từ cảnh này sang cảnh kia.

**Cấu trúc cần giữ:** hình dáng lớn quyết định mảng tranh; biến dạng vừa tạo chất liệu; chi tiết nhỏ tạo mép rách. Độ gồ ghề phải liên tục qua thời gian, không phát sinh ngẫu nhiên mới ở mỗi frame.

**Nghiệm thu:** dừng hình kiểm tra hình biên; phát chậm kiểm tra tính liên tục của từng chỗ lồi/lõm. Nếu cùng một hoa văn chạy lặp quanh vòng hoặc cả biên rung giật, chuyển động sẽ khác nguồn.

**Bản hiện tại:** dùng noise thủ tục thay mud texture; không thể gọi là đã khôi phục đúng bề mặt nguồn.

## FX03 — Mép phát sáng và ánh sáng lan

**Thấy:** biên chuyển cảnh sáng mạnh, có đoạn trắng/vàng nhạt, độ sáng thay đổi theo chất liệu. Tranh phía trong vẫn giữ được vải, khuôn mặt và cây.

**Xác nhận:** shader tăng sáng trong dải gần ngưỡng chuyển; mức tăng bị điều biến bởi noise/thời gian. Bloom sau ghép cảnh làm phần sáng lan ra.

**Điều khiển độc lập:** bề rộng dải sáng, cường độ dải sáng, độ ngắt quãng, ngưỡng bloom, bán kính và cường độ lan. Bật bloom lên toàn bộ áo trắng không thay thế được ánh sáng ở mép mask.

**Nghiệm thu:** kiểm tra đồng thời biên và vùng trắng trên quần áo. Biên đủ sáng nhưng nếp vải còn thấy; ánh sáng giảm khi vùng chuyển đi qua. Không cần một vành sáng cố định sau khi ảnh đã hiện hết.

**Bản hiện tại:** trắng lóa đã giảm; hình dải sáng và texture vẫn chưa khớp hoàn toàn.

## FX04 — Camera tiến/lùi và thay đổi phối cảnh

**Thấy:** trong đoạn vào, cảnh thay đổi quy mô; cánh tay/vật gần máy chiếm diện tích lớn rồi về bố cục hai bên. Nền và người không trượt cùng một tốc độ.

**Xác nhận:** timeline có camera position, target và FOV riêng. Thay đổi vị trí camera tạo thay đổi khoảng cách và tỷ lệ giữa các lớp; đổi FOV lại có tác động khác lên khung nhìn.

**Cần đo:** phải so ít nhất tâm đầu, bàn tay, đầu gối, ván trượt và hai điểm nền tại cùng pose. Chỉ so chiều rộng cả nhân vật không đủ phân biệt camera sai với scale asset sai.

**Nghiệm thu:** ngoài vị trí từng điểm, phải so các quan hệ trước/sau và phần nào bị cắt ở biên màn hình. Một ảnh phóng to có thể khớp một mốc nhưng sai toàn bộ quá trình.

**Bản hiện tại:** dùng camera 3D và có clock riêng, nhưng chưa đăng ký chính xác quỹ đạo với ảnh nguồn.

## FX05 — Camera nghiêng và cảm giác xoay quanh tâm

**Thấy:** hướng cảnh thay đổi trong lúc vùng mở biến dạng. Một phần cảm giác xoay còn đến từ vật thể trong tranh.

**Xác nhận:** camera roll đầu trong timeline khoảng 0,27 rad, tương đương 15,5°, về gần 0 tại mốc timeline 1. Timeline này không tự tương đương với giây trên video.

**Phân biệt:** camera xoay quanh trục nhìn, mask biến dạng và ván trượt xoay là ba chuyển động riêng. Không có bằng chứng cả bức tranh thực hiện một vòng 360°.

**Nghiệm thu:** theo hướng của các chi tiết nền ổn định sau khi loại phối cảnh và rung của máy quay ngoài. Việc xoay một ảnh chữ nhật hậu kỳ có thể làm lộ góc ảnh; đó là lỗi render, không phải chi tiết của mẫu.

**Bản hiện tại:** lỗi lộ góc ảnh đã được bỏ bằng cách dùng camera. Góc và nhịp còn cần khớp pose.

## FX06 — Thân người đi vào và khớp tay chân

**Thấy:** khoảng 0,9–1,1s tay áo/cánh tay đi vào trước, thân và mặt theo sau. Khoảng 1,2–1,4s chân/giày rõ hơn. Tới 1,4–1,8s hai người gần đủ, tư thế còn tiếp tục thay đổi.

**Xác nhận:** asset có bộ xương và nhiều kênh animation. Chuyển động gồm transform của toàn asset và tư thế tương đối của các khớp. Animation progress nguồn đi cả xuôi lẫn ngược qua các mốc, nên không tương đương phát một clip từ đầu đến cuối rồi lặp.

**Điều khiển:** clock vào cảnh; đoạn clip đang lấy mẫu; chiều phát/tiến trình clip; độ trễ của nhân vật; camera; phần bị mask che. Một bàn tay chưa thấy có thể đang ở ngoài camera hoặc đang bị mask che — hai trường hợp cần xử lý khác nhau.

**Nghiệm thu:** chọn mốc bàn tay/đầu gối/mặt, xác định vị trí màn hình và góc chi tương đối. Sau đó kiểm tra thứ tự đi vào. Tư thế đầu/cuối đúng nhưng vận tốc giữa hai mốc sai vẫn chưa giống.

**Bản hiện tại:** có rig duỗi/co; ánh xạ clock theo các mốc nhìn thấy; chưa đo từng khớp theo khung nguồn.

## FX07 — Ván trượt và các phụ kiện

**Thấy:** khoảng 1,3s ván trượt gần dọc, 1,6–1,8s nghiêng xuống; sau đó tiến gần ngang. Chân và ván không dừng cùng lúc. Túi/cốc và tay liên quan tạo các chi tiết chuyển động khác.

**Xác nhận:** GLB có các đối tượng/bộ phận riêng cho phụ kiện và các kênh animation liên quan. Cần giữ hệ tọa độ cha/con đúng để phụ kiện bám nhân vật khi thân đổi tư thế.

**Nghiệm thu:** so vị trí hai đầu ván, góc mặt ván và khoảng cách tới bàn chân. So cả thời điểm bắt đầu đổi góc và thời điểm giảm tốc. Không chỉ so góc ván ở hình cuối.

**Bản hiện tại:** có chuyển động phụ kiện từ clip; chưa xác nhận khớp toàn bộ quỹ đạo với nguồn.

## FX08 — Tranh cũ chuyển thành đường nét rồi hòa sang tranh mới

**Thấy:** cửa sổ 6,1–6,5s có vùng sáng mở ở giữa, các nét vải/người/cảnh cũ nổi thành đường bao, cảnh Sidekick dần thay thế. Cảnh mới cũng có đoạn đường nét trước khi trở thành hình bình thường.

**Xác nhận:** shader nguồn tính cạnh từ đạo hàm độ sáng `fwidth`, pha ảnh cũ với cạnh cũ và ảnh mới với cạnh mới; rồi ghép chúng qua mask. Dải glow nằm gần biên chuyển. Đây là nhiều thao tác cùng phối hợp.

**Thứ tự cần dựng:** giữ hai render riêng → lấy đường nét của từng render → tính mask → pha ảnh/cạnh ở từng phía theo tiến trình → ghép hai phía → bloom vùng sáng. Tên gọi fade đơn thuần không mô tả đủ.

**Nghiệm thu:** ở mốc giữa chuyển cảnh phải nhận ra các cấu trúc của tranh cũ trong dạng đường nét. Nếu chỉ có một đường sáng chạy qua hai ảnh trộn opacity thì thiếu lớp quan trọng.

**Bản hiện tại:** chưa tái dựng đầy đủ pha này; là một ưu tiên lớn để tăng độ giống.

## FX09 — Trượt lớp, chênh lệch chiều sâu và che khuất

**Thấy:** bàn tay hoặc tay áo gần máy đổi kích thước/đi qua khung khác với cây xa; vật thể trước người và cảnh xa có quan hệ che khuất ổn định. Ở Retail, thiết bị và trần vòm thay đổi phối cảnh rõ rệt.

**Xác nhận:** có scene 3D, camera và nhiều asset riêng; Retail còn chỉ định camera nhúng `posxxlcamera`. Không thể áp cùng một translate/scale lên cả cảnh rồi giữ được tất cả quan hệ này.

**Nghiệm thu:** theo ít nhất một điểm gần, một điểm trung cảnh và một điểm nền. Kiểm tra khoảng cách tương đối của chúng và đúng đối tượng nằm trước. Với camera nhúng phải giữ đúng transform từ đối tượng cha.

**Bản hiện tại:** có chiều sâu từ asset/camera; cần kiểm tra kỹ chuyển từ camera nhúng sang scene khác và pose nguồn.

## FX10 — Chữ lớn đi vào, rời lên trên; khung chữ làm điểm neo

**Thấy:** khung chữ hero giữ vị trí giữa lúc cảnh chuyển động. Ở Sidekick, tiêu đề lớn đi lên; khoảng 9,0–9,2s nó rời phần trên, mô tả và thẻ nhỏ trở nên nổi bật. Khối chữ không xoay cùng tranh.

**Điều khiển:** vị trí theo tiến trình cuộn; cửa sổ giữ tiêu đề; cửa sổ rời khỏi viewport; thứ tự giữa tiêu đề, mô tả và thẻ. Không có bằng chứng cần một hiệu ứng đánh máy cho từng ký tự.

**Nghiệm thu:** so baseline chữ với các mốc ổn định của viewport, không so với mép TV hoặc bàn phím trong video. Đo riêng mức dịch chuyển và mức mờ; không giả định chữ ra khỏi khung là do fade.

**Bản hiện tại:** khung chữ mảnh và thứ bậc đã được dựng; copy/form là thích nghi Video OS.

## FX11 — Nền kem mép rách đi lên che tranh

**Thấy:** xem ảnh nguyên khung 8,8 / 9,0 / 9,1 / 9,2s: vùng kem mép gồ ghề bắt đầu lộ khoảng 9,1–9,2s, rõ hơn ở 9,3–9,6s và gần phủ phần lớn màn hình cuối giây 9. Tranh vẫn ở phía sau trong quá trình này.

**Đính chính:** mốc 9,6s trong một số bản phân tích/cấu hình trước không phải thời điểm bắt đầu hiệu ứng. Đó là lúc vùng kem đã lên đáng kể. Cần phân biệt bắt đầu / rõ nhất / kết thúc.

**Điều khiển:** vị trí mép trên của lớp kem; hình dạng và mức biến đổi mép; vị trí camera/tranh phía sau; các thẻ ở trước. Mép rách chuyển động theo thời gian trong nguồn không được xem là đã khớp chỉ vì có một đường zigzag CSS.

**Nghiệm thu:** theo tọa độ mép giấy ở bên trái, giữa và bên phải qua từng mốc. Kiểm tra giấy che tranh theo không gian, không làm cả tranh mờ trắng cùng lúc. Khi giấy rời đi phải thấy đúng cảnh kế tiếp phía sau.

**Bản hiện tại:** đã có lớp nội dung đi lên trong flow; mép CSS tĩnh và nội dung minh họa chưa tương đương chuyển tiếp nguồn.

## FX12 — Hạt sáng, sao và chuyển động môi trường

**Thấy:** nền Sidekick có điểm sáng/sao; trong một số đoạn các vùng sáng và chi tiết môi trường tạo chiều sâu. Video quay ngoài cũng có nhiễu/phản xạ riêng, cần loại khỏi nhận định về web.

**Xác nhận:** cấu hình scene có particles, màu, kích thước, vị trí, opacity, pulse/blink và các tham số khác. Có tham số trong dữ liệu không đồng nghĩa đã xác nhận tất cả đều bật hoặc nhìn thấy rõ trong bản quay.

**Điều khiển:** phân bố trong không gian, kích thước điểm, mức sáng, nhịp nhấp nháy, tương tác với camera. Nhiễu dùng cho mask là một hệ khác với hạt sáng trong cảnh.

**Nghiệm thu:** hạt hỗ trợ chiều sâu, không phủ đầy form/chữ; so mật độ và độ sáng tương đối. Phải phân biệt điểm sao nằm trong tranh, particle động và phản xạ từ màn laptop.

**Bản hiện tại:** có lớp hạt đơn giản; chưa xác minh đầy đủ pulse/blink và mọi thông số nguồn.

## Hệ đồng bộ tạo cảm giác mượt

12 nhóm trên không nên dùng một clock tuyến tính chung. Cần đồng bộ bằng một tiến trình điều phối, nhưng mỗi nhóm có đoạn vào, độ trễ, đường cong vận tốc và điểm giữ riêng. Việc thay đổi rig đúng pose nhưng đổi camera sớm làm cả chuyển động trông sai; việc đổi cảnh sớm khi giấy chưa rời cũng làm cảm giác bị cắt.

Timeline nguồn có keyframe và tay nắm Bézier. Mốc đầu/cuối, vận tốc đầu/cuối và tính liên tục ở điểm nối cần được giữ. Nhịp chậm–nhanh–giảm tốc giải thích phần lớn cảm giác mượt; lắc sin mọi lớp không thay thế được.

Đoạn mở cần tự chạy khi scene sẵn sàng. Các chương sau trong video được quay khi có thao tác cuộn, nên giây trong bản quay không phải lịch tự động cho mọi người dùng. Với reduced motion vẫn cần hiển thị đầy đủ form và nội dung.

## Các điều chưa thể khẳng định

- Chưa đủ bằng chứng cho một vòng idle vô hạn đúng như nguồn; dữ liệu hero còn ghi autoplay/loop false. Phần idle sin hiện tại là bổ sung, không phải khôi phục chính xác.
- Chưa đo được mọi góc khớp từ video quay nghiêng; cần khớp pose với asset gốc.
- Chưa đo FPS/frame pacing độc lập để kết luận độ mượt chỉ từ việc timeline đổi giá trị.
- Chưa xác nhận motion blur hoặc DOF là hiệu ứng web riêng; mờ trong video có thể do camera quay ngoài.
- Trích ảnh chính xác bước 0,1s không đồng nghĩa bản dựng đã chính xác tới 0,1s ở mọi lớp.

## Thứ tự sửa dựa trên tác động thị giác

1. Căn camera và tư thế người/phụ kiện tại các mốc vào khung.
2. Dựng đầy đủ pha tranh → đường nét → tranh khi chuyển cảnh.
3. Căn hình dạng, tâm, tốc độ và chất liệu biên mask.
4. Khớp giấy đi lên/rời khung và thời điểm lộ cảnh sau.
5. Căn glow/bloom giữ được nếp vải, rồi hoàn thiện chữ/hạt/môi trường.

Mỗi hiệu ứng cần clip so sánh riêng và kiểm tra khi ghép chung. Đạt riêng lẻ chưa đủ nếu độ trễ giữa các lớp sai.
