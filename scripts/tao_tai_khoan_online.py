"""Create or reset an administrator account on a hosted database (e.g. Neon).

Run from the project root:
    .\\.venv\\Scripts\\python.exe scripts\\tao_tai_khoan_online.py

The connection string and passwords are typed with hidden input and are never printed.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.bootstrap import create_owner  # noqa: E402
from app.db import make_engine, make_session_factory, normalize_database_url  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def ask_password():
    while True:
        first = getpass.getpass("Mật khẩu mới (từ 12 ký tự, gõ không hiện chữ): ")
        if len(first) < 12:
            print("  Mật khẩu quá ngắn, cần ít nhất 12 ký tự.")
            continue
        if first.startswith(("postgres", "http")):
            print("  Đây trông giống chuỗi kết nối, không phải mật khẩu. Hãy nghĩ một mật khẩu mới.")
            continue
        if getpass.getpass("Nhập lại mật khẩu: ") != first:
            print("  Hai lần nhập không khớp, thử lại.")
            continue
        return first


def main():
    url = getpass.getpass("Dán chuỗi kết nối Neon (bắt đầu bằng postgresql://, gõ không hiện chữ): ").strip()
    if not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        print("Chuỗi không hợp lệ: phải bắt đầu bằng postgresql://. Có thể bạn đã dán nhầm địa chỉ web.")
        return 1
    url = normalize_database_url(url)
    try:
        parsed = make_url(url)
        print(f"Máy chủ cơ sở dữ liệu: {parsed.host}  |  database: {parsed.database}")
        print("(So sánh tên máy chủ này với DATABASE_URL trên Render: phải giống nhau.)")
        engine = make_engine(url)
        with make_session_factory(engine)() as db:
            names = [u.username for u in db.scalars(select(User).order_by(User.username))]
    except Exception as exc:  # noqa: BLE001
        print(f"Không kết nối được cơ sở dữ liệu: {type(exc).__name__}. Kiểm tra lại chuỗi kết nối.")
        return 1
    print("Tài khoản hiện có:", ", ".join(names) if names else "(chưa có)")
    username = input("Tên đăng nhập muốn tạo hoặc đặt lại mật khẩu [quanly]: ").strip() or "quanly"
    password = ask_password()
    if username in names:
        with make_session_factory(engine)() as db:
            user = db.scalar(select(User).where(User.username == username))
            user.password_hash = hash_password(password)
            user.active = True
            db.commit()
        print(f"Đã đặt lại mật khẩu cho tài khoản '{username}'.")
    else:
        result = create_owner(url, username, password, "Quản lý", "Studio")
        print(f"Đã tạo tài khoản '{result['username']}' với vai trò {result['role']}.")
    engine.dispose()
    print("Xong. Đăng nhập trên web bằng tên đăng nhập và mật khẩu vừa nhập.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
