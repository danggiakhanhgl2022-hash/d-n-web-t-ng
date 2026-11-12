# Phân tích hiệu ứng video tham chiếu

Phân tích tách riêng 12 nhóm hiệu ứng, cách kiểm chứng và đính chính mốc nền kem Sidekick nằm trong `DAC-TA-TUNG-HIEU-UNG.md`. Ảnh nguyên khung cho thấy nền kem đã bắt đầu lộ khoảng 9,1–9,2s; 9,6s là lúc lớp này đã lên đáng kể, không phải mốc bắt đầu.

Ngày 10/11/2026. Phạm vi: phân tích hiệu ứng và xác định khoảng cách của bản web; không thay mã sản phẩm trong lượt phân tích này.

## Bằng chứng và độ chắc chắn

- Video gốc 38,667s/30fps; bộ trích 387 ảnh theo bước 0,1s trong `runtime/reference-video/tenths`. Các cửa sổ 0,0–2,9s, 6,0–6,9s và các chuyển chương đã được xem qua contact sheet.
- Mã shader lưu cục bộ trong `runtime/reference-video/Background-DpyJh-o1.js`, đoạn `CrossFade`/`uI`: có tâm chiếu từ 3D, bù aspect, noise, mud normal, xử lý đường viền bằng đạo hàm độ sáng, ghép hai cảnh và tăng sáng tại biên.
- Timeline hero trong `frontend/public/renaissance/3d/HeroScene.theatre-project-state_15.json`: camera position/rotation/target/FOV và animation progress được điều khiển riêng.
- GLB hero có 8 skin, 15 mesh và clip `Scene` với 552 animation channel, dài 5 giây trong asset. Độ dài clip này không phải thời lượng đoạn hero trong video. Static config ghi `autoplay: false`, `Scene.loop: false`.

Phân biệt ba mức: quan sát trực tiếp trong ảnh; cơ chế xác nhận từ mã/asset; thông số phải hiệu chỉnh thêm. Không suy ra một quỹ đạo xương 3D duy nhất từ video quay laptop nghiêng.

## 1. Vùng tranh mở từ nền tối

### Nhìn thấy

Ban đầu phần lớn màn hình tối, chỉ có chữ nhỏ. Một mảng tranh sáng xuất hiện gần giữa, nở ra theo biên không đều. Đường biên có chỗ lồi/lõm lớn và chi tiết rách nhỏ; độ sáng ngắt quãng theo chất liệu. Vùng tranh chưa hiện vẫn tối, vùng đã mở nhìn thấy chi tiết cảnh bên trong.

### Cơ chế được xác nhận

Shader tính khoảng cách từ tâm để tạo vùng mở, có nhân tỷ lệ màn hình nhằm giữ hình tròn khi viewport rộng. Tâm có thể lấy từ vị trí 3D chiếu ra màn hình và chịu ảnh hưởng nhỏ của con trỏ. Khoảng cách được pha với một trường theo trục ngang; noise và texture mud làm lệch ngưỡng hiện hình. Vì vậy biên không phải một vòng tròn hoàn hảo hoặc một dãy cánh hoa lặp đều.

Có ba thang chi tiết cần giữ: hình mảng lớn; bề mặt gồ ghề vừa; các mép sáng nhỏ bị đứt/loang. Chỉ dùng một hàm sin theo góc tạo hoa văn tuần hoàn dễ bị nhìn thành cánh hoa. Chỉ tăng blur tạo một viền mờ đồng đều, mất chất liệu.

### Cảm giác xoay

Cảm giác xoay đến từ camera đổi hướng, phối cảnh cảnh 3D thay đổi và biên mask biến dạng. Chưa có bằng chứng cả bức tranh phải quay đủ 360°. Timeline gốc có camera roll đầu khoảng 0,27 rad (15,5°), rồi về gần 0 ở mốc timeline 1. Đây là đơn vị timeline nguồn, không được mặc định bằng giây trên video quay.

Xoay một ảnh render chữ nhật trong hậu kỳ làm xuất hiện góc ảnh hoặc vùng thiếu pixel. Muốn giữ cảnh phủ viewport phải xoay camera trong không gian hoặc render dư vùng; không để mép render target trở thành một phần hiệu ứng. Bản hiện tại đã bỏ lỗi xoay ảnh phẳng này.

## 2. Ánh sáng ở mép tranh và biến thành đường nét

### Nhìn thấy

Mép mở sáng mạnh nhưng thân tranh vẫn có chi tiết. Ở khoảng 6,1–6,5s, giữa hai cảnh xuất hiện vùng sáng, các đường bao người/vải/cảnh trở nên nổi rõ, rồi hình cũ nhường cho hình mới. Cảm giác là tranh bị bóc/tan thành đường nét chứ không chỉ đổi opacity.

### Cơ chế được xác nhận

Shader lấy độ sáng của ảnh rồi dùng `fwidth` để ước lượng cạnh. Nó pha ảnh cảnh cũ với phiên bản đường viền của cảnh cũ; đồng thời pha cảnh mới với đường viền của cảnh mới theo tiến trình. Mask sau đó quyết định vùng nào thuộc cảnh nào. Ánh sáng tại biên phụ thuộc khoảng cách tới ngưỡng và noise, rồi bloom làm phần sáng lan ra.

Đây không phải một bộ lọc viền bật suốt trang. Nó có cửa sổ thời gian trong chuyển cảnh. Cạnh áo, nét cây và vật thể được nhấn ngắn rồi trả về hình bình thường.

**Khoảng cách hiện tại:** shader tái dựng đã có vùng mở, noise và viền sáng, nhưng chưa tái tạo đầy đủ bước cảnh cũ/cảnh mới cùng chuyển sang đường nét như shader gốc. Đây là thiếu hụt quan trọng hơn việc thêm chuyển động nền.

## 3. Camera, thân người, tay chân và phụ kiện

### Camera

Camera thay đổi vị trí, hướng nhìn, góc nghiêng và FOV. Điều đó làm cánh tay gần camera lớn hơn, cảnh xa nhỏ hơn, hai người đi vào từ ngoài rìa và cây/nền trượt với tốc độ khác nhau. Di chuyển nguyên ảnh bằng CSS không tạo được đầy đủ thay đổi phối cảnh và che khuất này.

### Bộ xương/rig

Asset hero có bộ xương điều khiển và nhiều kênh animation. Đầu, cánh tay, bàn tay, chân và các phần liên quan không chỉ nằm trong một hình ảnh cố định. Muốn khớp tư thế cần lấy đúng clip, thời điểm trong clip và transform của asset, không chỉ dịch toàn bộ người từ trái/phải vào.

Timeline animation progress nguồn có cả tăng lẫn giảm: 1 → 0 → 1 → khoảng 0,09 qua các mốc. Đó là chuyển động qua lại theo tiến trình, không tương đương cho clip lặp đều từ đầu tới cuối. Cũng không nên đồng nhất clock của camera với clock của rig.

### Phụ kiện

Ván trượt đi từ gần dọc sang nghiêng và gần ngang trong lúc chân vẫn thay đổi. Túi, cốc và phần tay liên quan góp vào cảm giác có chiều sâu. Ván trượt là một chuyển động xoay riêng, không chứng minh toàn cảnh quay một vòng.

### Các mốc quan sát đầu video

| Video | Quan sát hiệu ứng |
| --- | --- |
| 0,0–0,1s | Nền tối/chữ nhỏ, chưa có mảng tranh lớn |
| 0,2s | Mảng tranh nhỏ và viền sáng xuất hiện |
| 0,3–0,4s | Mảng tranh mở nhanh, hướng cảnh và hình dạng biên thay đổi |
| 0,5–0,7s | Vùng mở chiếm phần lớn chiều cao, biên vẫn không đều |
| 0,8–0,9s | Mép tranh gần rìa; tay áo đỏ bắt đầu tiến vào từ phải |
| 1,0–1,1s | Cánh tay/ống tay đi vào trước, thân và mặt theo sau |
| 1,2–1,3s | Chân, giày và ván trượt dần vào khung; ván gần dọc |
| 1,4–1,5s | Hai nhân vật gần đủ, vẫn còn thay đổi tư thế/phối cảnh |
| 1,6–1,8s | Ván trượt nghiêng xuống; tay chân và vải ổn định dần |
| 1,9–2,2s | Giữ bố cục hai bên, vật thể còn dịch/đổi góc nhỏ |
| 3–5s | Chuyển động nhỏ còn thấy; chưa đủ bằng chứng để kết luận vòng idle tự chạy vô hạn |

Mốc quan sát có độ phân giải 0,1s; vị trí camera/khớp chưa được đo theo pixel đã đăng ký phối cảnh.

## 4. Vì sao chuyển động có cảm giác mượt

Mỗi nhóm có nhịp riêng: vùng mở chờ ngắn rồi nở nhanh; camera lùi/đổi góc; tay chân đi vào sau; phụ kiện còn tiếp tục xoay khi thân người gần ổn định; chữ và nội dung giữ thứ bậc dễ theo dõi. Tốc độ thay đổi trong từng đoạn thay vì tuyến tính đồng đều.

Giá trị nội suy và vận tốc ở các điểm nối đều quan trọng. Khớp đúng tư thế đầu/cuối nhưng nối bằng vận tốc không phù hợp vẫn tạo cảm giác giật. Việc thêm sin/lắc lên mọi lớp có thể khiến cảnh chuyển động nhiều hơn nhưng không tái tạo được biên độ, pha và điểm dừng của mẫu.

Một lần lấy mẫu 0,1s bỏ qua hai frame giữa mỗi cặp ảnh ở 30fps. Khi tìm chỗ giật hoặc mép chuyển chưa đúng, cần trở lại các frame cách nhau 1/30 giây quanh điểm đó. Tăng số ảnh không thay thế căn clock, phối cảnh và vận tốc.

## 5. Chữ, mục lục và nội dung nền kem

Khung chữ giữa màn hình là điểm neo thị giác trong lúc tranh/camera thay đổi. Chữ không xoay cùng toàn bộ tranh. Ở các chương sau, tiêu đề lớn đi vào rồi đi lên; mô tả/thẻ tiếp tục xuất hiện phía dưới. Chữ, tranh và các tấm nội dung có thứ tự lớp khác nhau.

Nền kem đi từ dưới lên, che tranh theo không gian; không chỉ là lớp trắng fade phủ cả viewport. Tranh phía sau được giữ trong khung nhìn một đoạn, tạo cảm giác nội dung lướt trước tranh. Khi chuyển tiếp, phần giấy phía trên rời đi để lộ cảnh tiếp theo. Độ cao thẻ và thứ tự che khuất ảnh hưởng trực tiếp đến cảm giác này.

Mục lục và header cần đổi màu khi nền từ tối sang kem. Khối nhập liệu phải giữ ổn định để đọc/gõ. Form đăng nhập là phần thích nghi của Video OS; video gốc không có cùng form đó.

## 6. Các họ chuyển cảnh trong video

| Họ hiệu ứng | Bằng chứng | Điều cần giữ |
| --- | --- | --- |
| Mở từ tối | 0,0–1,2s | Tâm mở, mép gồ ghề, ánh sáng cục bộ, camera đồng bộ |
| Tranh → tranh bằng vùng sáng/đường nét | 6,1–6,5s | Ghép hai render, mép và đường bao cùng biến đổi |
| Giấy/nội dung → tranh mới | Khoảng 10,1s, 13,1s và các chương sau | Lớp trước rời khung, lộ cảnh sau; có mép không đều |
| Tranh → thẻ/nền kem | Khoảng 9,6s, 14,4s, 21,9s… | Thẻ lên từ dưới, cảnh sau giữ vị trí và chiều sâu |
| Vật thể + camera đặc thù | Retail 18–22s | Thiết bị xoay/tiến/lùi, camera mở rộng và nhìn lên trần |
| Mô hình/vật thể khác | Finance/Shipping | Đồng xu/vật thể và chuyển động nhân vật theo asset riêng |

Không có căn cứ để dùng cùng một vòng tròn, cùng thời lượng và cùng quỹ đạo cho mọi chương.

## 7. Mở trang tự chạy và chuyển động theo cuộn

Đoạn mở cần tự chạy khi mở web và scene sẵn sàng; người dùng không cần cuộn mới thấy nhân vật đi vào. Các phần giới thiệu về sau được video quay trong khi có thao tác cuộn. Mốc 6,1s hoặc 18,2s là thời gian trong bản quay, không phải lịch tự động bắt mọi khách truy cập phải xem.

`autoplay: false` và `loop: false` trong cấu hình nguồn cũng là lý do không nên suy diễn mọi vật thể đều có một vòng lặp tự chạy liên tục. Bản web hiện tại thêm chuyển động idle nhỏ theo yêu cầu trước đó; đó là lựa chọn thích nghi, chưa được chứng minh là đúng vòng lặp nguồn.

## 8. Đánh giá bản hiện tại và thứ tự cần xử lý

| Thành phần | Trạng thái hiện tại |
| --- | --- |
| Tự mở và hiện hai người | Có, đã kiểm tra |
| Loại bỏ góc render target khi xoay | Đã xử lý bằng camera 3D |
| Mép nhiễu và ánh sáng | Có bản tái dựng; chưa đúng texture/mức biến dạng nguồn |
| Chi tiết vải/áo tránh trắng lóa | Đã cải thiện sau giảm đèn và bloom |
| Chuyển cảnh thành đường nét | Chưa đầy đủ; cần ưu tiên tiếp |
| Camera và pose khớp từng mốc | Chưa được đăng ký chính xác theo khung nguồn |
| Vận tốc/độ trễ từng nhóm | Đã có clock riêng; còn phải đo quanh các điểm nối |
| Idle chạy lặp | Có phần bổ sung; không nên gọi là đã khôi phục đúng nguồn |
| Giấy che tranh, lớp nội dung đi lên | Đã dựng lại cấu trúc; hình/thẻ là nội dung thích nghi |

Thứ tự làm để tăng độ giống: khớp camera và rig ở các pose quan trọng → khôi phục pha ảnh thành đường nét khi đổi cảnh → dùng đúng trường nhiễu/texture và đường cong mở → căn ánh sáng theo từng cảnh → căn vận tốc, chữ và giấy. Không dùng việc test chức năng xanh hoặc số ảnh đã trích để thay kết luận về chất lượng hiệu ứng.
