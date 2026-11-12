"""Create or reset an administrator account on a hosted database (e.g. Neon).

Run from the project root:
    .\\.venv\\Scripts\\python.exe scripts\\tao_tai_khoan_online.py

The connection string and passwords are typed with hidden input and are never printed.
"""
import getpass
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.bootstrap import create_owner  # noqa: E402
from app.db import make_engine, make_session_factory, normalize_database_url  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def read_clipboard():
    for exe in ("powershell", "pwsh"):
        try:
            out = subprocess.run([exe, "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                                 capture_output=True, text=True, timeout=15)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
    return ""


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
    print("Bước 1: vào Neon > Kết nối > bấm 'Sao chép đoạn mã' để chép chuỗi kết nối vào clipboard.")
    input("Bước 2: chép xong thì nhấn Enter ở đây (chuỗi sẽ được đọc từ clipboard, không hiện lên màn hình): ")
    pattern = r"postgres(?:ql)?(?:\+psycopg)?://[^\s'\"]+"
    raw = read_clipboard()
    match = re.search(pattern, raw)
    if not match:
        print(f"Clipboard không có 'postgresql://' (độ dài nội dung: {len(raw)} ký tự, bắt đầu bằng: {raw[:10]!r}).")
        print("Cách khác: nhấn chuột phải trong cửa sổ này để DÁN chuỗi. Chuỗi sẽ hiện trên màn hình, đừng chụp màn hình lúc này.")
        raw = input("Dán chuỗi kết nối Neon rồi nhấn Enter: ").strip()
        match = re.search(pattern, raw)
    if not match:
        print(f"Vẫn không thấy 'postgresql://' (độ dài: {len(raw)} ký tự). Lấy lại chuỗi từ Neon > Kết nối > Sao chép đoạn mã.")
        return 1
    url = match.group(0)
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
