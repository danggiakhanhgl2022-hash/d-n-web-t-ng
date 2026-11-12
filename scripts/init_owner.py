"""Create the real local owner without shipping a shared/default password."""
import os
import secrets
import sys
from manage import ROOT, ENV, configure

configure()
os.environ.update(ENV)
sys.path.insert(0, str(ROOT / "backend"))
from app.bootstrap import create_owner

credential_path = ROOT / "TAI-KHOAN-CUC-BO.txt"
if credential_path.exists():
    print("Local owner credential file already exists; no account was changed.")
else:
    password = secrets.token_urlsafe(24)
    create_owner(database_url=ENV["DATABASE_URL"], username="owner", password=password,
                 display_name="Chủ sở hữu", tenant_name="Không gian của bạn")
    credential_path.write_text(
        "TÀI KHOẢN CỤC BỘ — CHẶNG A\n\n"
        "Địa chỉ: http://127.0.0.1:3100\n"
        "Tên đăng nhập: owner\n"
        f"Mật khẩu: {password}\n\n"
        "Tài khoản này có quyền quản trị và duyệt trong không gian cục bộ của bạn.\n"
        "Chưa có dự án khách hàng nào được tạo hoặc duyệt sẵn.\n",
        encoding="utf-8"
    )
    print("Local owner created. Open TAI-KHOAN-CUC-BO.txt for the login; password was not printed.")
