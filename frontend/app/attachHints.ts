// Câu hỏi nào có chỗ đính kèm ảnh, video, ghi âm ngay trong câu, và dòng gợi ý hiện kèm.
export const ATTACH_HINT: Record<string, string> = {
  "P2": "Gửi kèm brief, kịch bản, video cũ hoặc video mẫu nếu có.",
  "A1": "Gửi kèm logo của đơn vị nếu có.",
  "A11": "Gửi kèm hình hoặc video thể hiện đúng cảm giác anh chị muốn.",
  "A12": "Gửi kèm logo, ảnh sản phẩm hoặc hình người thật nếu có.",
  "A13": "Gửi kèm tài liệu ghi câu chữ phải giữ nguyên nếu có.",
  "A18": "Gửi kèm giấy tờ chứng minh quyền dùng ảnh, nhạc, giọng nếu có.",
  "B2.1": "Chọn tệp brief hoặc kịch bản từ máy, hoặc dán link vào ô trên.",
  "B3.4": "Gửi kèm giấy chứng nhận hoặc số liệu cần đối chiếu.",
  "B4.1": "Chọn video có sẵn từ máy, hoặc dán link vào ô trên.",
  "B4.3": "Chọn file gốc từ máy, hoặc dán link Drive vào ô trên.",
  "B5.1": "Chọn video mẫu từ máy, hoặc dán link vào ô trên.",
  "C2.3": "Gửi kèm file dòng chữ pháp lý bắt buộc.",
  "C4.2": "Gửi kèm file mẫu hoặc thiết kế gốc nếu có.",
  "C5.1": "Gửi kèm ảnh thật của nhân vật hoặc sản phẩm cần giống hệt.",
  "C6.1": "Gửi kèm ảnh các địa điểm quay nếu có.",
  "C7.1": "Gửi kèm giọng mẫu anh chị thích, hoặc bấm Ghi âm để đọc thử vài câu.",
  "C7.2": "Chọn bài nhạc mẫu từ máy, hoặc dán link vào ô trên.",
  "C7.3": "Gửi kèm file âm thanh hiệu ứng bắt buộc.",
};
export const DEFAULT_LIMITS = {image: 25 * 1048576, audio: 60 * 1048576, video: 200 * 1048576};
