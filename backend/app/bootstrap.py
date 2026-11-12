"""Create a real local administrator, never seed fabricated project approvals."""
import argparse
import getpass
import json
import sys
from sqlalchemy import select
from .db import Base, make_engine, make_session_factory
from .models import Tenant, User, AuditEvent
from .security import hash_password


def create_owner(database_url, username, password, display_name="Owner", tenant_name="Studio"):
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        if db.scalar(select(User).where(User.username == username)):
            raise ValueError("Tên đăng nhập đã tồn tại; không ghi đè tài khoản.")
        tenant = Tenant(name=tenant_name)
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, username=username, display_name=display_name, role="ADMIN", password_hash=hash_password(password))
        db.add(user)
        db.flush()
        db.add(AuditEvent(tenant_id=tenant.id, actor_id=user.id, action="OWNER_BOOTSTRAPPED", data={"username": username, "role": "ADMIN"}))
        db.commit()
        result = {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role, "tenant_id": tenant.id}
    engine.dispose()
    return result


def main():
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", default="Người quản lý")
    parser.add_argument("--tenant-name", default="Studio")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Cần DATABASE_URL hoặc --database-url.")
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("Mật khẩu (tối thiểu12 ký tự): ")
    print(json.dumps(create_owner(args.database_url, args.username, password, args.display_name, args.tenant_name), ensure_ascii=False))


if __name__ == "__main__":
    main()
