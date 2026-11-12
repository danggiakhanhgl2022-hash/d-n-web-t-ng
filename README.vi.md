# Video OS — Tiếp nhận khách hàng & cổng thông tin

> 🇬🇧 English: [README.md](README.md)

Ứng dụng web tự vận hành cho studio làm video quảng cáo. Biến bước đầu rối nhất của một dự án — thu thập yêu cầu của khách — thành quy trình có cấu trúc, truy vết được: **bộ câu hỏi → câu trả lời và nguồn → xác nhận → Folder Thông Tin → xem xét và duyệt**.

Giao diện là trải nghiệm "điện ảnh" cuộn theo trang (Next.js + three.js); phía máy chủ là FastAPI có phân quyền chặt, chống CSRF và nhật ký kiểm toán đầy đủ.

## Điểm nổi bật

- **Tiếp nhận có cấu trúc:** 51 câu hỏi có phiên bản (16 câu lõi + 35 câu theo nhánh). Khách tự trả lời và tải ảnh, video, âm thanh, tệp mẫu lên.
- **Dựa trên bằng chứng:** tệp nguồn có checksum SHA-256, kiểm lại khi dùng. Prefill chỉ lấy các dòng đánh dấu rõ (`CORE-02: ...`), không suy đoán và không gọi LLM.
- **Cổng duyệt:** PM/Admin xác nhận, rồi duyệt, yêu cầu sửa hoặc từ chối một snapshot bất biến. Sửa sau khi duyệt làm snapshot thành bản lịch sử và khóa bàn giao.
- **Xuất file:** ZIP Folder Thông Tin (manifest có checksum), JSON, DOCX, PDF; xuất Excel cho sổ làm việc của studio.
- **Phân quyền:** `ADMIN`, `PM`, `ACCOUNT`, `VIEWER`, kiểm ở máy chủ và tách theo từng tenant.

## Kiến trúc

Trình duyệt → Next.js (giao diện, header bảo mật, chuyển `/api`) → FastAPI (xác thực, kiểm tra dữ liệu, duyệt, xuất) → PostgreSQL + thư mục lưu tệp (tên UUID, có checksum).

| Thư mục | Vai trò |
|---|---|
| `backend/` | FastAPI, mô hình, kiểm tra, trích xuất, snapshot/export, Alembic |
| `frontend/` | Giao diện Next.js / TypeScript, cảnh three.js |
| `tests/` | Kiểm thử tích hợp với dữ liệu QA riêng |
| `scripts/` | Trình chạy `manage.py`, bootstrap, công cụ kiểm tra |
| `docs/` | Quyết định, hợp đồng, phạm vi, bằng chứng kiểm |
| `runtime/` | Dữ liệu, log, tệp cục bộ — **không đưa lên git** |

## Bắt đầu

Yêu cầu: Python 3.11+, Node.js tương thích Next.js 16, npm, Docker Desktop (cho PostgreSQL).

```powershell
python scripts/manage.py setup   # venv, thư viện khóa phiên bản, PostgreSQL, migration, tài khoản chủ
python scripts/manage.py start   # backend :8100, frontend :3100
```

Mở <http://127.0.0.1:3100>. Tài khoản chủ được tạo lúc bootstrap và ghi vào file cục bộ không đưa lên git; mã nguồn không có tài khoản hay mật khẩu mặc định. Trên Windows dùng `CAP-NHAT-VA-CHAY.bat` để dựng lại và chạy, `DUNG-UNG-DUNG.bat` để dừng.

Cấu hình: sao chép `.env.example` thành `.env` và điền giá trị thật (không commit). Khi triển khai online đặt `APP_ENV=production`, `COOKIE_SECURE=true`, và `TRUST_PROXY=true` nếu chạy sau reverse proxy do bạn kiểm soát.

Kiểm thử: `python -m pytest` (dùng SQLite tạm), `cd frontend; npm run typecheck; npm run build`.

## Triển khai online

`render.yaml` dựng sẵn PostgreSQL, API và web trên Render. Hướng dẫn từng bước, danh sách việc cần làm trước khi công khai và kiểm tra sau khi lên mạng nằm ở [docs/DEPLOY.md](docs/DEPLOY.md). Biến `BACKEND_URL` (frontend) trỏ tới địa chỉ API.

## Bảo mật

Tóm tắt (chi tiết ở [SECURITY.md](SECURITY.md)): băm mật khẩu PBKDF2-SHA256 600.000 vòng; phiên phía máy chủ, cookie `HttpOnly` + `SameSite=Strict` + `Secure` khi chạy thật; CSRF cho mọi thao tác ghi; giới hạn đăng nhập sai; cô lập dữ liệu theo tenant; kiểm tệp tải lên theo đuôi, dung lượng và chữ ký tệp; header bảo mật ở cả hai tầng (CSP chạy chế độ báo cáo trước); nhật ký kiểm toán chỉ ghi thêm.

## Phạm vi

Đã làm chặng 01 (cổng thông tin). Các chặng sau (sinh nội dung, dựng, bàn giao) chưa nằm trong phạm vi. Lưu tệp ở ổ đĩa cục bộ; khi đưa lên Internet cần HTTPS, PostgreSQL được quản lý, sao lưu ngoài máy và bộ giới hạn tốc độ dùng chung.

## Tài nguyên bên thứ ba

Một số cảnh 3D và texture trong `frontend/public/renaissance/` có nguồn từ bên thứ ba, **không** thuộc giấy phép của dự án này. Hãy thay bằng tài nguyên của bạn trước khi công khai hoặc triển khai.

Chi tiết xem [NOTICE.md](NOTICE.md).

## Giấy phép

Mã nguồn theo giấy phép [MIT](LICENSE); tài nguyên bên thứ ba không thuộc phạm vi này.
