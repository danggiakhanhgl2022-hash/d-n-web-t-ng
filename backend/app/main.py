from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import time
import zipfile
from types import SimpleNamespace

from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .db import Base, make_engine, make_session_factory
from .models import Tenant, User, LoginSession, Project, Answer, Source, Snapshot, Approval, Feedback, AuditEvent, ShareLink, SourceMeta, now, uid
from .security import hash_password, check_password, burn_password_check, token_hash
from .questionnaire import QUESTIONS, SECTIONS, CATALOG, CORE_CODES, TEMPLATE_VERSION, canonical, semantic_errors, evaluate, delivery_matrix, valid_scope_ids, annotate_answers
from zoneinfo import ZoneInfo

BRAND = json.loads((Path(__file__).with_name("brand.json")).read_text(encoding="utf-8"))
CODE_PATTERN = r"[PABCDE]\d{1,2}(?:\.\d{1,2})?"


def today_vn():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
from .exports import export_package


class Problem(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(Input):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1000)


class UserInput(LoginInput):
    display_name: str = Field(min_length=1, max_length=200)
    role: str


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=200)
    customer: str = Field(default="", max_length=200)


class RevisionInput(Input):
    expected_revision: int = Field(ge=1)


class AnswerInput(RevisionInput):
    value: object = None
    raw_text: str | None = Field(default=None, max_length=100000)
    status: str = "ANSWERED_UNCONFIRMED"
    scope_id: str = Field(default="", max_length=100)
    source_id: str | None = None
    evidence_locator: str | None = Field(default=None, max_length=1000)


class ConfirmInput(RevisionInput):
    question_codes: list[str] = Field(min_length=1, max_length=100)
    scope_id: str = Field(default="", max_length=100)


class PrefillInput(RevisionInput):
    source_id: str


class FeedbackInput(RevisionInput):
    message: str = Field(min_length=1, max_length=10000)


class DecisionInput(RevisionInput):
    snapshot_id: str
    content_hash: str
    decision: str
    notes: str = Field(default="", max_length=10000)


def serialize(row, exclude=()):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in exclude}


def audit(db, user, action, data, project=None):
    db.add(AuditEvent(tenant_id=user.tenant_id, project_id=project.id if project else None, actor_id=user.id, action=action, data=data))


def answers_for(db, p):
    rows = [serialize(a, ("id", "project_id")) for a in db.scalars(select(Answer).where(Answer.project_id == p.id).order_by(Answer.question_code, Answer.scope_id))]
    return annotate_answers(rows)


def sources_for(db, p):
    rows = []
    for s in db.scalars(select(Source).where(Source.project_id == p.id).order_by(Source.created_at)):
        row = serialize(s, ("storage_name", "project_id"))
        meta = db.get(SourceMeta, s.id)
        row["via"] = meta.via if meta else "STAFF"
        row["note"] = meta.note if meta else ""
        row["question_code"] = meta.question_code if meta else None
        rows.append(row)
    return rows


def source_path(storage, source):
    root = Path(storage).resolve()
    path = (root / source.storage_name).resolve()
    if path.parent != root or not path.is_file():
        raise Problem(409, "SOURCE_INTEGRITY", "File nguồn không tồn tại hoặc sai vị trí.")
    data = path.read_bytes()
    if len(data) != source.size or hashlib.sha256(data).hexdigest() != source.sha256:
        raise Problem(409, "SOURCE_INTEGRITY", "File nguồn không còn khớp checksum đã đăng ký.")
    return path


def snapshot_payload(db, p):
    answers = answers_for(db, p)
    if p.template_version != TEMPLATE_VERSION:
        raise Problem(409, "NEEDS_MIGRATION_REVIEW", "Phiên bản bộ câu hỏi của dự án chưa có adapter để đọc/chuyển đổi.")
    return {"schema_version": "3.0", "gate_id": "STAGE_01_INFORMATION", "template_version": p.template_version, "questionnaire_definition": QUESTIONS, "project": serialize(p, ("tenant_id", "status", "updated_at")), "answers": answers, "sources": sources_for(db, p), "validation": evaluate(answers), "delivery_matrix": delivery_matrix(answers)}


def verify_snapshot(s):
    if hashlib.sha256(s.canonical_json.encode()).hexdigest() != s.hash:
        raise Problem(409, "SNAPSHOT_INTEGRITY", "Snapshot không khớp checksum.")
    payload = json.loads(s.canonical_json)
    if canonical(payload) != s.canonical_json:
        raise Problem(409, "SNAPSHOT_INTEGRITY", "Snapshot không còn ở dạng canonical.")
    return payload


def stage02(db, p):
    approved = db.scalars(select(Approval).where(Approval.project_id == p.id).order_by(Approval.created_at.desc())).first()
    if p.status != "APPROVED" or not approved or approved.decision != "APPROVED" or approved.stage_version != p.revision:
        return {"allowed": False, "reason": "Gate 01 chưa có quyết định duyệt hợp lệ cho phiên bản hiện hành."}
    s = db.get(Snapshot, approved.snapshot_id)
    if not s or s.hash != approved.content_hash:
        return {"allowed": False, "reason": "Snapshot không hợp lệ."}
    verify_snapshot(s)
    return {"allowed": True, "reason": "Đã có snapshot Gate 01 được duyệt; Stage 02 chưa triển khai.", "snapshot_id": s.id}


def detail(db, p):
    result = serialize(p, ("tenant_id",))
    result["answers"] = answers_for(db, p)
    result["sources"] = sources_for(db, p)
    result["feedback"] = [serialize(f, ("project_id",)) for f in db.scalars(select(Feedback).where(Feedback.project_id == p.id).order_by(Feedback.created_at))]
    approvals = [serialize(a, ("project_id",)) for a in db.scalars(select(Approval).where(Approval.project_id == p.id).order_by(Approval.created_at))]
    result["approvals"] = approvals
    result["snapshots"] = []
    for s in db.scalars(select(Snapshot).where(Snapshot.project_id == p.id).order_by(Snapshot.created_at)):
        decision = next((a for a in reversed(approvals) if a["snapshot_id"] == s.id), None)
        result["snapshots"].append({"id": s.id, "hash": s.hash, "stage_version": s.stage_version, "created_at": s.created_at, "status": "STALE" if s.stage_version != p.revision else decision["decision"] if decision else "PENDING"})
    result["validation"] = evaluate(result["answers"])
    result["stage02"] = stage02(db, p)
    result["delivery_matrix"] = delivery_matrix(result["answers"])
    link = db.scalar(select(ShareLink).where(ShareLink.project_id == p.id, ShareLink.revoked == False).order_by(ShareLink.created_at.desc()))  # noqa: E712
    live = bool(link and datetime.fromisoformat(link.expires_at) > datetime.now(timezone.utc))
    result["client_link"] = {"active": live, "path": f"/gui/{link.token}" if live and link.token else None, "expires_at": link.expires_at if link else None, "submitted_at": link.submitted_at if link else None}
    return result


def touch(db, p, user, expected, action, data):
    previous_status = p.status
    status = "STALE" if previous_status in {"APPROVED", "STALE"} else "DRAFT"
    updated = db.execute(update(Project).where(Project.id == p.id, Project.revision == expected).values(revision=expected + 1, status=status, updated_at=now()).execution_options(synchronize_session=False))
    if updated.rowcount != 1:
        raise Problem(409, "REVISION_CONFLICT", "Dữ liệu đã thay đổi. Hãy tải lại trước khi lưu.")
    db.refresh(p)
    audit(db, user, action, {"previous_revision": expected, "revision": p.revision, **data}, p)


def require_role(user, roles):
    if user.role not in roles:
        raise Problem(403, "FORBIDDEN", "Tài khoản không có quyền thực hiện thao tác này.")


MEDIA_LIMITS = {"image": 25 * 1024 * 1024, "audio": 60 * 1024 * 1024, "video": 200 * 1024 * 1024}
MEDIA_TYPES = {".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".gif": "image",
               ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".ogg": "audio", ".aac": "audio",
               ".mp4": "video", ".mov": "video", ".webm": "video", ".m4v": "video"}


def media_signature_ok(data, extension):
    head = data[:16]
    if extension == ".png":
        return head.startswith(b"\x89PNG")
    if extension in {".jpg", ".jpeg"}:
        return head.startswith(b"\xff\xd8\xff")
    if extension == ".gif":
        return head.startswith(b"GIF8")
    if extension == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if extension == ".wav":
        return head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if extension == ".mp3":
        return head.startswith(b"ID3") or (head[:1] == b"\xff" and (head[1] & 0xE0) == 0xE0)
    if extension == ".ogg":
        return head.startswith(b"OggS")
    if extension == ".aac":
        return head[:1] == b"\xff" and (head[1] & 0xF0) == 0xF0
    if extension in {".m4a", ".mp4", ".mov", ".m4v"}:
        return head[4:8] == b"ftyp" or head[4:8] in {b"moov", b"mdat", b"wide", b"free"}
    if extension == ".webm":
        return head.startswith(b"\x1aE\xdf\xa3")
    return False


def extract_source(data, extension):
    if extension in MEDIA_TYPES:
        if not media_signature_ok(data, extension):
            raise Problem(422, "INVALID_SOURCE", "Nội dung tệp không khớp đuôi tệp; hãy gửi lại tệp gốc.")
        return "", "MEDIA"
    if extension in {".txt", ".md"}:
        if b"\x00" in data:
            raise Problem(422, "INVALID_SOURCE", "File văn bản chứa dữ liệu nhị phân.")
        try:
            return data.decode("utf-8-sig"), "EXTRACTED"
        except UnicodeDecodeError:
            raise Problem(422, "INVALID_ENCODING", "Cần văn bản mã hóa UTF-8.")
    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise Problem(422, "INVALID_SOURCE", "File PDF không có chữ ký định dạng hợp lệ.")
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 200:
                return "", "MANUAL_REQUIRED"
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return text[:1000000], "EXTRACTED" if text.strip() else "MANUAL_REQUIRED"
        except Exception:
            return "", "MANUAL_REQUIRED"
    if extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                entries = z.infolist()
                if len(entries) > 1000 or sum(e.file_size for e in entries) > 30000000 or any(e.file_size > 10000000 or (e.compress_size and e.file_size / e.compress_size > 200) for e in entries):
                    raise Problem(422, "ARCHIVE_LIMIT", "DOCX vượt giới hạn giải nén an toàn.")
                if "word/document.xml" not in z.namelist() or any(".." in e.filename.split("/") for e in entries):
                    raise Problem(422, "INVALID_SOURCE", "Cấu trúc DOCX không hợp lệ.")
            from docx import Document
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
            text += "\n" + "\n".join(" | ".join(c.text for c in r.cells) for t in doc.tables for r in t.rows)
            return text[:1000000], "EXTRACTED" if text.strip() else "MANUAL_REQUIRED"
        except Problem:
            raise
        except Exception:
            raise Problem(422, "INVALID_SOURCE", "Không đọc được DOCX hợp lệ.")
    raise Problem(422, "UNSUPPORTED_SOURCE", "Chỉ nhận TXT, MD, DOCX hoặc PDF.")


PRODUCTION = os.getenv("APP_ENV", "development").lower() == "production"
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"


def client_ip(request):
    """Địa chỉ khách. Chỉ tin X-Forwarded-For khi TRUST_PROXY=true (đã đặt sau reverse proxy đáng tin), nếu không kẻ tấn công tự giả IP để né giới hạn."""
    if TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "local"


def create_app(database_url=None, storage_dir=None):
    engine = make_engine(database_url)
    factory = make_session_factory(engine)
    storage = Path(storage_dir or os.getenv("STORAGE_DIR", "./data/sources")).resolve()
    storage.mkdir(parents=True, exist_ok=True)
    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        yield
    app = FastAPI(title="AI Video OS — Chặng A", version="0.1.0", lifespan=lifespan,
                  docs_url=None if PRODUCTION else "/docs", redoc_url=None if PRODUCTION else "/redoc", openapi_url=None if PRODUCTION else "/openapi.json")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        if PRODUCTION:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response
    app.state.engine, app.state.session_factory, app.state.storage_dir = engine, factory, storage
    failures = {}

    @app.exception_handler(Problem)
    async def problem_handler(request, e):
        return JSONResponse({"error": {"code": e.code, "message": e.message, "details": e.details}}, status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def input_error(request, e):
        return JSONResponse({"error": {"code": "INVALID_INPUT", "message": "Dữ liệu gửi lên không hợp lệ.", "details": [{"loc": list(x["loc"]), "msg": x["msg"]} for x in e.errors()]}}, status_code=422)

    def db_session():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def auth(request: Request, db=Depends(db_session)):
        token = request.cookies.get("session_token", "")
        session = db.get(LoginSession, token_hash(token)) if token else None
        if not session or datetime.fromisoformat(session.expires_at) <= datetime.now(timezone.utc):
            raise Problem(401, "UNAUTHENTICATED", "Vui lòng đăng nhập.")
        user = db.get(User, session.user_id)
        if not user or not user.active:
            raise Problem(401, "UNAUTHENTICATED", "Phiên đăng nhập không còn hiệu lực.")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(request.headers.get("X-CSRF-Token", "").encode("utf-8"), session.csrf_token.encode("utf-8")):
            raise Problem(403, "CSRF_INVALID", "CSRF token không hợp lệ; vui lòng đăng nhập lại.")
        request.state.login_session = session
        return user

    def project(db, user, project_id, expected=None):
        stmt = select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id, Project.status != "DELETED")
        if expected is not None:
            stmt = stmt.with_for_update()
        p = db.scalar(stmt)
        if not p:
            raise Problem(404, "NOT_FOUND", "Không tìm thấy dự án.")
        if expected is not None and p.revision != expected:
            raise Problem(409, "REVISION_CONFLICT", "Dữ liệu đã thay đổi. Hãy tải lại trước khi lưu.", {"revision": p.revision})
        return p

    def source(db, p, source_id):
        s = db.scalar(select(Source).where(Source.id == source_id, Source.project_id == p.id))
        if not s:
            raise Problem(404, "NOT_FOUND", "Không tìm thấy nguồn chứng minh.")
        return s

    def user_info(user):
        return serialize(user, ("password_hash", "active"))

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "scope": "STAGE_01", "generation_available": False}

    @app.post("/api/v1/auth/login")
    def login(body: LoginInput, request: Request, response: Response, db=Depends(db_session)):
        key = (client_ip(request), body.username.lower())
        history = [v for v in failures.get(key, []) if time.monotonic() - v < 300]
        if len(history) >= 8:
            raise Problem(429, "LOGIN_RATE_LIMIT", "Quá nhiều lần đăng nhập sai. Vui lòng thử lại sau 5 phút.")
        user = db.scalar(select(User).where(User.username == body.username))
        if not user:
            burn_password_check(body.password)
        if not user or not user.active or not check_password(body.password, user.password_hash):
            failures[key] = [*history, time.monotonic()]
            raise Problem(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu chưa đúng.")
        failures.pop(key, None)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        session = LoginSession(id=token_hash(token), user_id=user.id, csrf_token=csrf, expires_at=(datetime.now(timezone.utc) + timedelta(hours=12)).isoformat())
        db.add(session)
        audit(db, user, "LOGIN", {})
        response.set_cookie("session_token", token, httponly=True, samesite="strict", secure=os.getenv("COOKIE_SECURE", "true" if PRODUCTION else "false").lower() == "true", max_age=43200, path="/")
        return {"user": user_info(user), "csrf_token": csrf}

    @app.get("/api/v1/auth/me")
    def me(request: Request, user=Depends(auth)):
        return {"user": user_info(user), "csrf_token": request.state.login_session.csrf_token}

    @app.post("/api/v1/auth/logout")
    def logout(request: Request, response: Response, user=Depends(auth), db=Depends(db_session)):
        db.delete(request.state.login_session)
        audit(db, user, "LOGOUT", {})
        response.delete_cookie("session_token", path="/")
        return {"ok": True}

    @app.post("/api/v1/users", status_code=201)
    def add_user(body: UserInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN"})
        if body.role not in {"ADMIN", "PM", "ACCOUNT", "VIEWER"}:
            raise Problem(422, "INVALID_ROLE", "Vai trò không hợp lệ.")
        if db.scalar(select(User).where(User.username == body.username)):
            raise Problem(409, "USERNAME_EXISTS", "Tên đăng nhập đã tồn tại.")
        try:
            encoded = hash_password(body.password)
        except ValueError as e:
            raise Problem(422, "WEAK_PASSWORD", str(e))
        created = User(tenant_id=user.tenant_id, username=body.username, display_name=body.display_name, password_hash=encoded, role=body.role)
        db.add(created)
        db.flush()
        audit(db, user, "USER_CREATED", {"user_id": created.id, "role": created.role})
        return user_info(created)

    @app.get("/api/v1/questions")
    def questions(user=Depends(auth)):
        return {"template_version": TEMPLATE_VERSION, "sections": SECTIONS, "questions": QUESTIONS}

    @app.get("/api/v1/brand")
    def brand():
        return BRAND

    @app.get("/api/v1/projects")
    def projects(user=Depends(auth), db=Depends(db_session)):
        links = {}
        for link in db.scalars(select(ShareLink).where(ShareLink.tenant_id == user.tenant_id).order_by(ShareLink.created_at)):
            links[link.project_id] = link
        items = []
        for p in db.scalars(select(Project).where(Project.tenant_id == user.tenant_id, Project.status != "DELETED").order_by(Project.updated_at.desc())):
            row = serialize(p, ("tenant_id", "template_version"))
            link = links.get(p.id)
            row["client_link"] = bool(link)
            row["client_submitted_at"] = link.submitted_at if link else None
            items.append(row)
        return {"items": items}

    @app.post("/api/v1/projects", status_code=201)
    def create_project(body: ProjectInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        if not body.name.strip():
            raise Problem(422, "INVALID_INPUT", "Tên dự án không được để trống.")
        p = Project(tenant_id=user.tenant_id, name=body.name.strip(), customer=body.customer.strip())
        db.add(p)
        db.flush()
        audit(db, user, "PROJECT_CREATED", {"revision": p.revision}, p)
        return detail(db, p)

    @app.get("/api/v1/projects/{project_id}")
    def get_project(project_id: str, user=Depends(auth), db=Depends(db_session)):
        return detail(db, project(db, user, project_id))

    @app.delete("/api/v1/projects/{project_id}", status_code=204)
    def delete_project(project_id: str, body: RevisionInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, body.expected_revision)
        updated = db.execute(update(Project).where(
            Project.id == p.id, Project.tenant_id == user.tenant_id,
            Project.revision == body.expected_revision, Project.status != "DELETED"
        ).values(status="DELETED", revision=body.expected_revision + 1, updated_at=now()).execution_options(synchronize_session=False))
        if updated.rowcount != 1:
            raise Problem(409, "REVISION_CONFLICT", "Dữ liệu đã thay đổi. Hãy tải lại trước khi xóa.")
        db.refresh(p)
        audit(db, user, "PROJECT_DELETED", {"previous_revision": body.expected_revision, "revision": p.revision}, p)
        return Response(status_code=204)

    def apply_answer(db, p, actor, code, body):
        if code not in CATALOG:
            raise Problem(422, "UNKNOWN_QUESTION", "Mã câu hỏi không tồn tại.")
        if p.template_version != TEMPLATE_VERSION:
            has_answers = db.scalar(select(Answer.id).where(Answer.project_id == p.id).limit(1))
            if has_answers:
                raise Problem(409, "NEEDS_MIGRATION_REVIEW", "Dự án dùng bộ câu hỏi cũ và đã có câu trả lời; tạo dự án mới cho bộ câu hỏi v3.")
            p.template_version = TEMPLATE_VERSION
        if body.status not in {"ANSWERED_UNCONFIRMED", "UNKNOWN", "NEEDS_CONSULTATION", "NOT_APPLICABLE", "CONFLICTED"}:
            raise Problem(422, "INVALID_ANSWER_STATUS", "Không được tự đặt trạng thái đã xác nhận.")
        try:
            encoded = canonical(body.value)
        except (ValueError, TypeError, UnicodeError):
            raise Problem(422, "INVALID_VALUE", "Giá trị phải là JSON hợp lệ.")
        if len(encoded) > 100000:
            raise Problem(422, "ANSWER_TOO_LARGE", "Câu trả lời quá dài.")
        if body.source_id:
            source(db, p, body.source_id)
        if body.scope_id:
            if body.scope_id not in valid_scope_ids(answers_for(db, p)):
                raise Problem(422, "INVALID_SCOPE", "Bộ câu hỏi v3 không nhận câu trả lời theo phạm vi riêng; dùng bảng yêu cầu theo cảnh (D1).")
        a = db.scalar(select(Answer).where(Answer.project_id == p.id, Answer.question_code == code, Answer.scope_id == body.scope_id))
        before = serialize(a) if a else None
        if not a:
            a = Answer(project_id=p.id, question_code=code, scope_id=body.scope_id, revision=1)
            db.add(a)
        else:
            a.revision += 1
        a.value, a.raw_text, a.status = body.value, body.raw_text, body.status
        a.source_id, a.evidence_locator = body.source_id, body.evidence_locator
        a.confirmed_by, a.confirmed_at = None, None
        db.flush()
        touch(db, p, actor, body.expected_revision, "ANSWER_REVISED", {"question_code": code, "scope_id": body.scope_id, "before": before, "after": serialize(a)})

    @app.put("/api/v1/projects/{project_id}/answers/{code}")
    def save_answer(project_id: str, code: str, body: AnswerInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, body.expected_revision)
        apply_answer(db, p, user, code, body)
        return detail(db, p)

    @app.post("/api/v1/projects/{project_id}/confirm")
    def confirm(project_id: str, body: ConfirmInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM"})
        p = project(db, user, project_id, body.expected_revision)
        if body.scope_id and body.scope_id not in valid_scope_ids(answers_for(db, p)):
            raise Problem(422, "INVALID_SCOPE", "Phạm vi đã bị gỡ hoặc không còn duy nhất trong ma trận bàn giao.")
        found = []
        errors = []
        for code in dict.fromkeys(body.question_codes):
            a = db.scalar(select(Answer).where(Answer.project_id == p.id, Answer.question_code == code, Answer.scope_id == body.scope_id))
            if not a or a.status in {"UNKNOWN", "NEEDS_CONSULTATION", "CONFLICTED", "NOT_APPLICABLE"}:
                errors.append({"question_code": code, "message": "Cần câu trả lời rõ và giải quyết xung đột trước xác nhận."})
                continue
            for error in semantic_errors(code, a.value, today=today_vn()):
                errors.append({"question_code": code, "message": error})
            found.append(a)
        if errors:
            raise Problem(422, "CONFIRMATION_BLOCKED", "Một số câu trả lời chưa hợp lệ để xác nhận.", errors)
        for a in found:
            before = serialize(a)
            a.status, a.confirmed_by, a.confirmed_at = "CONFIRMED", user.id, now()
            a.revision += 1
            audit(db, user, "ANSWER_CONFIRMED", {"before": before, "question_code": a.question_code, "answer_revision": a.revision}, p)
        touch(db, p, user, body.expected_revision, "ANSWERS_CONFIRMED", {"question_codes": body.question_codes, "scope_id": body.scope_id})
        db.flush()
        return detail(db, p)

    async def ingest_source(db, p, file, expected, actor, via="STAFF", note="", question_code=None):
        filename = file.filename or ""
        if not filename or any(v in filename for v in ["/", "\\", ":", "\x00"]) or len(filename) > 240:
            raise Problem(422, "INVALID_FILENAME", "Tên file không hợp lệ.")
        extension = Path(filename).suffix.lower()
        allowed_mimes = {".txt": {"text/plain"}, ".md": {"text/plain", "text/markdown", "application/octet-stream"}, ".pdf": {"application/pdf"}, ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}}
        media_kind = MEDIA_TYPES.get(extension)
        mime_type = (file.content_type or "application/octet-stream").split(";")[0]
        if media_kind:
            if not (mime_type.startswith(media_kind + "/") or mime_type in {"application/octet-stream", "video/quicktime"}
                    or (media_kind == "video" and mime_type.startswith("audio/")) or (media_kind == "audio" and mime_type.startswith("video/"))):
                raise Problem(422, "UNSUPPORTED_SOURCE", "Loại tệp không khớp đuôi tệp.")
            limit = MEDIA_LIMITS[media_kind]
        elif extension in allowed_mimes and mime_type in allowed_mimes[extension]:
            limit = 10 * 1024 * 1024
        else:
            raise Problem(422, "UNSUPPORTED_SOURCE", "Chỉ nhận văn bản (TXT, MD, DOCX, PDF), ảnh (PNG, JPG, WEBP, GIF), âm thanh (MP3, WAV, M4A, OGG) và video (MP4, MOV, WEBM).")
        data = await file.read(limit + 1)
        if not data or len(data) > limit:
            raise Problem(413, "SOURCE_TOO_LARGE", f"Tệp phải có nội dung và không vượt {limit // (1024 * 1024)} MB.")
        text, parser_status = extract_source(data, extension)
        s = Source(project_id=p.id, filename=filename, storage_name=uid() + extension, mime_type=file.content_type, sha256=hashlib.sha256(data).hexdigest(), size=len(data), extracted_text=text, extraction_status=parser_status)
        db.add(s)
        db.flush()
        if via != "STAFF" or note or question_code:
            db.add(SourceMeta(source_id=s.id, via=via, note=(note or "")[:1000], question_code=question_code))
        path = storage / s.storage_name
        path.write_bytes(data)
        try:
            touch(db, p, actor, expected, "SOURCE_ADDED", {"source_id": s.id, "sha256": s.sha256, "parser_status": parser_status, "via": via})
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return s

    def fill_answer_from_file(db, p, actor, code, src):
        """Câu hỏi "link hoặc tên file": tải tệp lên cũng là đã trả lời, tự ghi tên tệp để khỏi gõ lại."""
        first = CATALOG[code]["fields"][0] if code else None
        if first and len(CATALOG[code]["fields"]) == 1 and first["type"] == "text":
            existing = db.scalar(select(Answer).where(Answer.project_id == p.id, Answer.question_code == code, Answer.scope_id == ""))
            current = existing.value.get(first["id"]) if existing and isinstance(existing.value, dict) else ""
            if not (current or "").strip():
                apply_answer(db, p, actor, code, AnswerInput(expected_revision=p.revision, value={first["id"]: f"Đã gửi tệp: {src.filename}"}))

    @app.post("/api/v1/projects/{project_id}/sources", status_code=201)
    async def upload_source(project_id: str, file: UploadFile = File(...), expected_revision: int = Form(...), note: str = Form(""), question_code: str = Form(""), user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, expected_revision)
        code = question_code.strip() or None
        if code and code not in CATALOG:
            code = None
        src = await ingest_source(db, p, file, expected_revision, user, note=note.strip(), question_code=code)
        fill_answer_from_file(db, p, user, code, src)
        return detail(db, p)

    @app.delete("/api/v1/projects/{project_id}/sources/{source_id}")
    def remove_source(project_id: str, source_id: str, expected_revision: int, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, expected_revision)
        src = source(db, p, source_id)
        if db.scalar(select(Answer.id).where(Answer.source_id == src.id).limit(1)):
            raise Problem(409, "SOURCE_IN_USE", "Tệp này đang được dùng làm căn cứ cho một câu trả lời, nên chưa gỡ được.")
        meta = db.get(SourceMeta, source_id)
        name = src.storage_name
        if meta:
            db.delete(meta)
            db.flush()
        db.delete(src)
        db.flush()
        touch(db, p, user, expected_revision, "SOURCE_REMOVED", {"source_id": source_id, "filename": src.filename})
        (storage / name).unlink(missing_ok=True)
        return detail(db, p)

    # ---- Link riêng cho khách gửi tệp (không cần tài khoản) ----
    def link_for(db, token):
        row = db.scalar(select(ShareLink).where(ShareLink.token_hash == token_hash(token or "")))
        if not row or row.revoked or datetime.fromisoformat(row.expires_at) <= datetime.now(timezone.utc):
            raise Problem(404, "LINK_INVALID", "Đường link không còn hiệu lực. Hãy nhờ người gửi cấp link mới.")
        p = db.get(Project, row.project_id)
        if not p or p.status == "DELETED":
            raise Problem(404, "LINK_INVALID", "Đường link không còn hiệu lực. Hãy nhờ người gửi cấp link mới.")
        return row

    @app.post("/api/v1/projects/{project_id}/share-link", status_code=201)
    def create_share_link(project_id: str, body: dict | None = None, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id)
        days = min(max(int((body or {}).get("days", 14)), 1), 60)
        for old in db.scalars(select(ShareLink).where(ShareLink.project_id == p.id, ShareLink.revoked == False)):  # noqa: E712
            old.revoked = True
        token = secrets.token_urlsafe(24)
        expires = datetime.now(timezone.utc) + timedelta(days=days)
        db.add(ShareLink(tenant_id=p.tenant_id, project_id=p.id, token_hash=token_hash(token), token=token, created_by=user.id, expires_at=expires.isoformat()))
        audit(db, user, "SHARE_LINK_CREATED", {"days": days}, p)
        return {"token": token, "path": f"/gui/{token}", "expires_at": expires.isoformat()}

    @app.delete("/api/v1/projects/{project_id}/share-link")
    def revoke_share_link(project_id: str, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id)
        count = 0
        for old in db.scalars(select(ShareLink).where(ShareLink.project_id == p.id, ShareLink.revoked == False)):  # noqa: E712
            old.revoked = True
            count += 1
        audit(db, user, "SHARE_LINK_REVOKED", {"count": count}, p)
        return {"revoked": count}

    def public_view(db, link):
        p = db.get(Project, link.project_id)
        files = []
        for src in db.scalars(select(Source).where(Source.project_id == p.id).order_by(Source.created_at)):
            meta = db.get(SourceMeta, src.id)
            if meta and meta.via == "CLIENT_LINK":
                files.append({"id": src.id, "filename": src.filename, "size": src.size, "created_at": src.created_at, "note": meta.note, "question_code": meta.question_code})
        used = sum(f["size"] for f in files)
        return {"project": p.name, "customer": p.customer, "files": files, "limits": {"max_files": link.max_files, "max_bytes": link.max_bytes, "image": MEDIA_LIMITS["image"], "audio": MEDIA_LIMITS["audio"], "video": MEDIA_LIMITS["video"]}, "used_bytes": used, "expires_at": link.expires_at}

    starts = {}

    @app.post("/api/v1/public/start", status_code=201)
    def public_start(request: Request, db=Depends(db_session)):
        """Khách vào web và bấm Bắt đầu: tự mở một đơn và nhận link riêng, nhân viên không phải làm gì."""
        host = client_ip(request)
        stamp = time.time()
        recent = [t for t in starts.get(host, []) if stamp - t < 3600]
        total = sum(1 for times in starts.values() for t in times if stamp - t < 3600)
        if len(recent) >= 8 or total >= 200:
            raise Problem(429, "TOO_MANY_STARTS", "Bạn mở phiếu quá nhiều lần trong một giờ. Hãy quay lại link đã có hoặc thử lại sau.")
        starts[host] = recent + [stamp]
        tenant = db.scalar(select(Tenant).order_by(Tenant.id))
        owner = db.scalar(select(User).where(User.tenant_id == tenant.id, User.active == True, User.role == "ADMIN").order_by(User.id)) if tenant else None  # noqa: E712
        if not owner:
            raise Problem(503, "NOT_READY", "Studio chưa sẵn sàng nhận phiếu, bạn thử lại sau nhé.")
        p = Project(tenant_id=tenant.id, name="Khách mới " + datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m %H:%M"), customer="")
        db.add(p)
        db.flush()
        token = secrets.token_urlsafe(24)
        db.add(ShareLink(tenant_id=tenant.id, project_id=p.id, token_hash=token_hash(token), token=token, created_by=owner.id,
                         expires_at=(datetime.now(timezone.utc) + timedelta(days=60)).isoformat()))
        audit(db, owner, "PROJECT_CREATED", {"revision": p.revision, "via": "CLIENT_SELF_START"}, p)
        return {"token": token, "path": f"/gui/{token}"}

    @app.get("/api/v1/public/{token}")
    def public_info(token: str, db=Depends(db_session)):
        return public_view(db, link_for(db, token))

    # Phiếu khách gọn: tập trung video giới thiệu sản phẩm và quảng cáo mạng xã hội, chia thành từng bước.
    # Thứ tự: mục đích và loại video trước, "đã từng làm video chưa" để cuối. Nhân viên vẫn thấy đủ bộ câu hỏi.
    CLIENT_STEPS = [
        {"id": "S1", "title": "Bạn cần video gì", "subtitle": "Mục đích, hình thức, bạn đã có ý tưởng hay kịch bản chưa", "part": "Phần A", "codes": ["A3", "P3", "P2", "A4"]},
        {"id": "S2", "title": "Nội dung chính", "subtitle": "Điều quan trọng nhất và cảm giác mong muốn", "part": "Phần A", "codes": ["A5", "C2.1", "A11"]},
        {"id": "S3", "title": "Hình thức video", "subtitle": "Số lượng, khung hình, nơi đăng, giọng đọc", "part": "Phần A", "codes": ["A7", "A8", "A9", "A10", "C7.1"]},
        {"id": "S4", "title": "Bạn đã có gì", "subtitle": "Tư liệu, điều cần tránh, quyền dùng AI", "part": "Phần B", "codes": ["A12", "A13", "A17"]},
        {"id": "S5", "title": "Thời gian và chi phí", "subtitle": "Khi nào cần và ngân sách dự kiến", "part": "Phần B", "codes": ["P4", "A15"]},
        {"id": "S6", "title": "Cách liên hệ", "subtitle": "Để studio gửi báo giá cho bạn", "part": "Phần B", "codes": ["A1", "A2"]},
        {"id": "S7", "title": "Một câu cuối", "subtitle": "Giúp studio chọn cách trao đổi phù hợp", "part": "Phần B", "codes": ["P1"]},
    ]
    STEP_OF = {c: st["id"] for st in CLIENT_STEPS for c in st["codes"]}
    CLIENT_ORDER = [c for st in CLIENT_STEPS for c in st["codes"]]
    CLIENT_CODES = {q["code"] for q in QUESTIONS if q["code"] in STEP_OF and q.get("audience") != "internal"}

    def client_sections(applicable, required, answers):
        app, req = set(applicable), set(required)
        done = {a["question_code"] for a in answers if a.get("value") is not None}
        out = []
        for st in CLIENT_STEPS:
            codes = [c for c in st["codes"] if c in app]
            out.append({"id": st["id"], "applicable": bool(codes), "total": len(codes), "required": sum(1 for c in codes if c in req),
                        "answered": sum(1 for c in codes if c in done), "confirmed": sum(1 for c in codes if c in done), "issues": 0})
        return out

    def client_view(db, link):
        p = db.get(Project, link.project_id)
        answers = [a for a in answers_for(db, p) if not a.get("scope_id") and a["question_code"] in CLIENT_CODES]
        for a in answers:
            for key in ("source_id", "evidence_locator", "confirmed_by", "confirmed_at", "raw_text"):
                a.pop(key, None)
        full = evaluate(answers_for(db, p))
        keep = lambda items: [x for x in items if x.get("question_code") in CLIENT_CODES]
        validation = {**full, "blockers": keep(full["blockers"]), "clarifications": keep(full["clarifications"]),
                      "applicable_codes": [c for c in full["applicable_codes"] if c in CLIENT_CODES],
                      "required_codes": [c for c in full["required_codes"] if c in CLIENT_CODES],
                      }
        validation["sections"] = client_sections(validation["applicable_codes"], validation["required_codes"], answers)
        view = public_view(db, link)
        return {"id": "me", "name": p.name, "customer": p.customer, "revision": p.revision, "status": "DRAFT", "answers": answers,
                "validation": validation, "sources": view["files"], "feedback": [], "approvals": [], "snapshots": [],
                "submitted_at": link.submitted_at, "limits": view["limits"], "used_bytes": view["used_bytes"], "expires_at": link.expires_at}

    @app.get("/api/v1/public/{token}/questions")
    def public_questions(token: str, db=Depends(db_session)):
        link_for(db, token)
        by_code = {q["code"]: q for q in QUESTIONS}
        questions = [json.loads(json.dumps(by_code[c])) for c in CLIENT_ORDER if c in CLIENT_CODES]
        for q in questions:
            q["section"] = STEP_OF[q["code"]]
            q["group"] = "A"
        for q in questions:  # gợi ý dành cho nhân viên không hợp với khách
            for f in q["fields"]:
                if "tab Tài liệu" in (f.get("example") or ""):
                    f["example"] = "Dán link, hoặc bấm “Thêm ảnh, video hoặc ghi âm” bên dưới"
        return {"template_version": TEMPLATE_VERSION, "sections": [{k: st[k] for k in ("id", "title", "subtitle", "part")} for st in CLIENT_STEPS], "questions": questions}

    @app.get("/api/v1/public/{token}/project")
    def public_project(token: str, db=Depends(db_session)):
        return client_view(db, link_for(db, token))

    @app.put("/api/v1/public/{token}/answers/{code}")
    def public_save_answer(token: str, code: str, body: AnswerInput, db=Depends(db_session)):
        link = link_for(db, token)
        if code not in CLIENT_CODES:
            raise Problem(403, "FORBIDDEN", "Câu này do studio điền.")
        if body.scope_id or body.source_id:
            raise Problem(422, "INVALID_INPUT", "Khách không dùng phạm vi riêng hay nguồn tham chiếu.")
        p = db.scalar(select(Project).where(Project.id == link.project_id).with_for_update())
        creator = db.get(User, link.created_by)
        actor = SimpleNamespace(id=creator.id if creator else "client-link", tenant_id=link.tenant_id)
        body.expected_revision = p.revision
        apply_answer(db, p, actor, code, body)
        value = body.value if isinstance(body.value, dict) else {}
        text = lambda key: value.get(key).strip()[:200] if isinstance(value.get(key), str) else ""
        if code == "A1":  # tên dự án và đơn vị: để nhân viên nhìn danh sách là biết đơn nào
            p.name = text("project") or p.name
            p.customer = text("org") or p.customer
        elif code == "A2" and not p.customer.strip():
            p.customer = text("name")
        if link.submitted_at:
            link.submitted_at = None
        return client_view(db, link)

    @app.delete("/api/v1/public/{token}/files/{source_id}")
    def public_delete_file(token: str, source_id: str, db=Depends(db_session)):
        link = link_for(db, token)
        p = db.scalar(select(Project).where(Project.id == link.project_id).with_for_update())
        src = db.scalar(select(Source).where(Source.id == source_id, Source.project_id == p.id))
        meta = db.get(SourceMeta, source_id) if src else None
        if not src or not meta or meta.via != "CLIENT_LINK":
            raise Problem(404, "NOT_FOUND", "Không tìm thấy tệp này.")
        if db.scalar(select(Answer.id).where(Answer.source_id == src.id).limit(1)):
            raise Problem(409, "SOURCE_IN_USE", "Tệp này đã được studio dùng làm căn cứ, hãy nhắn studio nếu muốn gỡ.")
        creator = db.get(User, link.created_by)
        actor = SimpleNamespace(id=creator.id if creator else "client-link", tenant_id=link.tenant_id)
        name = src.storage_name
        db.delete(meta)
        db.flush()
        db.delete(src)
        db.flush()
        touch(db, p, actor, p.revision, "SOURCE_REMOVED_BY_CLIENT", {"source_id": source_id, "filename": src.filename})
        (storage / name).unlink(missing_ok=True)
        return client_view(db, link)

    @app.post("/api/v1/public/{token}/submit")
    def public_submit(token: str, db=Depends(db_session)):
        link = link_for(db, token)
        view = client_view(db, link)
        missing = [b for b in view["validation"]["blockers"] if b.get("code") != "NEEDS_CONFIRMATION"]
        if missing:
            raise Problem(422, "INCOMPLETE", "Còn câu bắt buộc chưa trả lời.", [{"question_code": b["question_code"], "message": b["message"]} for b in missing])
        link.submitted_at = now()
        creator = db.get(User, link.created_by)
        p = db.get(Project, link.project_id)
        if creator:
            audit(db, creator, "CLIENT_SUBMITTED", {"via": "CLIENT_LINK"}, p)
        return client_view(db, link)

    @app.post("/api/v1/public/{token}/files", status_code=201)
    async def public_upload(token: str, file: UploadFile = File(...), note: str = Form(""), question_code: str = Form(""), db=Depends(db_session)):
        link = link_for(db, token)
        p = db.scalar(select(Project).where(Project.id == link.project_id).with_for_update())
        view = public_view(db, link)
        if len(view["files"]) >= link.max_files:
            raise Problem(429, "LINK_FULL", f"Đã đủ {link.max_files} tệp cho đơn này.")
        if view["used_bytes"] >= link.max_bytes:
            raise Problem(429, "LINK_FULL", "Đã đạt tổng dung lượng cho phép của đơn này.")
        code = question_code.strip() or None
        if code and code not in CATALOG:
            code = None
        creator = db.get(User, link.created_by)
        actor = SimpleNamespace(id=creator.id, tenant_id=link.tenant_id) if creator else SimpleNamespace(id="client-link", tenant_id=link.tenant_id)
        src = await ingest_source(db, p, file, p.revision, actor, via="CLIENT_LINK", note=note.strip(), question_code=code)
        # Câu hỏi "link hoặc tên file": tải tệp lên cũng là đã trả lời, tự ghi tên tệp để khách không phải gõ lại.
        fill_answer_from_file(db, p, actor, code, src)
        return client_view(db, link)

    @app.get("/api/v1/projects/{project_id}/sources/{source_id}/download")
    def download_source(project_id: str, source_id: str, user=Depends(auth), db=Depends(db_session)):
        p = project(db, user, project_id)
        s = source(db, p, source_id)
        data = source_path(storage, s).read_bytes()
        return Response(data, media_type=s.mime_type, headers={"Content-Disposition": f"attachment; filename=source-{s.id}{Path(s.filename).suffix}", "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})

    @app.post("/api/v1/projects/{project_id}/prefill")
    def prefill(project_id: str, body: PrefillInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, body.expected_revision)
        s = source(db, p, body.source_id)
        source_path(storage, s)
        matches = list(re.finditer(r"(?m)^\s*(" + CODE_PATTERN + r")\s*[:：]\s*(.*)$", s.extracted_text))
        changed = []
        for match in matches:
            code, raw = match.groups()
            if code not in CATALOG or not raw.strip():
                continue
            if len(raw) > 100000:
                raise Problem(422, "PREFILL_TOO_LARGE", "Một câu đề xuất vượt giới hạn độ dài cho phép.")
            try:
                def reject_nonfinite(constant):
                    raise ValueError("Non-finite JSON number")
                value = json.loads(raw, parse_constant=reject_nonfinite)
            except (json.JSONDecodeError, ValueError):
                value = raw.strip()
            text_fields = [f for f in CATALOG[code]["fields"] if f["type"] in {"text", "textarea"}]
            if isinstance(value, str) and len(CATALOG[code]["fields"]) == 1 and text_fields:
                value = {text_fields[0]["id"]: value}
            try:
                encoded_value = canonical(value)
                encoded_value.encode("utf-8")
            except (ValueError, TypeError, UnicodeError):
                raise Problem(422, "INVALID_PREFILL_VALUE", "Đề xuất chứa JSON hoặc ký tự Unicode không hợp lệ.")
            if len(encoded_value) > 100000:
                raise Problem(422, "PREFILL_TOO_LARGE", "Một câu đề xuất vượt giới hạn độ dài cho phép.")
            a = db.scalar(select(Answer).where(Answer.project_id == p.id, Answer.question_code == code, Answer.scope_id == ""))
            if a and canonical(a.value) == canonical(value):
                continue
            before = serialize(a) if a else None
            if not a:
                a = Answer(project_id=p.id, question_code=code, scope_id="", value=value, raw_text=raw, status="PROPOSED_FROM_SOURCE", revision=1, source_id=s.id, evidence_locator=f"line:{s.extracted_text[:match.start()].count(chr(10))+1}")
                db.add(a)
            else:
                a.status, a.confirmed_by, a.confirmed_at = "CONFLICTED", None, None
                a.revision += 1
                audit(db, user, "ANSWER_CONFLICTED", {"question_code": code, "existing": before, "proposed_value": value, "source_id": s.id}, p)
            changed.append(code)
        if changed:
            db.flush()
            touch(db, p, user, body.expected_revision, "SOURCE_PREFILL", {"source_id": s.id, "question_codes": changed, "adapter": "EXPLICIT_MARKER_PARSER_NO_LLM"})
        return detail(db, p)

    @app.post("/api/v1/projects/{project_id}/validate")
    def validate(project_id: str, user=Depends(auth), db=Depends(db_session)):
        return detail(db, project(db, user, project_id))

    @app.post("/api/v1/projects/{project_id}/feedback")
    def feedback(project_id: str, body: FeedbackInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, body.expected_revision)
        if not body.message.strip():
            raise Problem(422, "INVALID_INPUT", "Góp ý không được để trống.")
        f = Feedback(project_id=p.id, actor_id=user.id, message=body.message.strip())
        db.add(f)
        audit(db, user, "FEEDBACK_ADDED", {"message": body.message.strip()}, p)
        db.flush()
        return detail(db, p)

    @app.post("/api/v1/projects/{project_id}/submit")
    def submit(project_id: str, body: RevisionInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM", "ACCOUNT"})
        p = project(db, user, project_id, body.expected_revision)
        validation = evaluate(answers_for(db, p))
        if not validation["can_submit"]:
            raise Problem(422, "GATE_BLOCKED", "Chưa đủ điều kiện đưa Folder Thông Tin vào duyệt.", validation["blockers"])
        if p.status == "APPROVED":
            raise Problem(409, "ALREADY_APPROVED", "Phiên bản này đã được duyệt.")
        for s in db.scalars(select(Source).where(Source.project_id == p.id)):
            source_path(storage, s)
        payload = snapshot_payload(db, p)
        encoded = canonical(payload)
        content_hash = hashlib.sha256(encoded.encode()).hexdigest()
        s = db.scalars(select(Snapshot).where(Snapshot.project_id == p.id, Snapshot.stage_version == p.revision, Snapshot.hash == content_hash)).first()
        if not s:
            s = Snapshot(project_id=p.id, stage_version=p.revision, hash=content_hash, canonical_json=encoded)
            db.add(s)
            db.flush()
        p.status, p.updated_at = "IN_REVIEW", now()
        audit(db, user, "SUBMITTED_FOR_REVIEW", {"snapshot_id": s.id, "content_hash": s.hash, "stage_version": s.stage_version}, p)
        db.flush()
        return detail(db, p)

    @app.post("/api/v1/projects/{project_id}/decision")
    def decide(project_id: str, body: DecisionInput, user=Depends(auth), db=Depends(db_session)):
        require_role(user, {"ADMIN", "PM"})
        p = project(db, user, project_id, body.expected_revision)
        if body.decision not in {"APPROVED", "CHANGES_REQUESTED", "REJECTED"}:
            raise Problem(422, "INVALID_DECISION", "Quyết định duyệt không hợp lệ.")
        s = db.scalar(select(Snapshot).where(Snapshot.id == body.snapshot_id, Snapshot.project_id == p.id))
        if not s or s.stage_version != p.revision or s.hash != body.content_hash:
            raise Problem(409, "STALE_APPROVAL", "Snapshot/hash/phiên bản không khớp dữ liệu hiện hành.")
        payload = verify_snapshot(s)
        if canonical(snapshot_payload(db, p)) != s.canonical_json:
            raise Problem(409, "STALE_APPROVAL", "Nội dung hiện hành đã khác snapshot.")
        if p.status != "IN_REVIEW":
            raise Problem(409, "NOT_IN_REVIEW", "Chỉ được quyết định cho phiên bản đang chờ duyệt.")
        if body.decision == "APPROVED" and not evaluate(answers_for(db, p))["can_submit"]:
            raise Problem(422, "GATE_BLOCKED", "Còn blocker chưa được xử lý.")
        for row in db.scalars(select(Source).where(Source.project_id == p.id)):
            source_path(storage, row)
        a = Approval(project_id=p.id, snapshot_id=s.id, stage_version=s.stage_version, content_hash=s.hash, actor_id=user.id, decision=body.decision, notes=body.notes)
        db.add(a)
        p.status, p.updated_at = body.decision, now()
        audit(db, user, "GATE_DECISION", {"snapshot_id": s.id, "content_hash": s.hash, "decision": body.decision, "notes": body.notes}, p)
        db.flush()
        return detail(db, p)

    @app.get("/api/v1/projects/{project_id}/stage02")
    def handoff(project_id: str, user=Depends(auth), db=Depends(db_session)):
        p = project(db, user, project_id)
        result = stage02(db, p)
        if result["allowed"]:
            for s in db.scalars(select(Source).where(Source.project_id == p.id)):
                source_path(storage, s)
        return result

    @app.get("/api/v1/projects/{project_id}/audit")
    def get_audit(project_id: str, user=Depends(auth), db=Depends(db_session)):
        p = project(db, user, project_id)
        return {"items": [serialize(e) for e in db.scalars(select(AuditEvent).where(AuditEvent.project_id == p.id, AuditEvent.tenant_id == user.tenant_id).order_by(AuditEvent.created_at))]}

    @app.get("/api/v1/projects/{project_id}/package")
    def package(project_id: str, format: str = Query("zip"), snapshot_id: str | None = None, user=Depends(auth), db=Depends(db_session)):
        p = project(db, user, project_id)
        if format not in {"zip", "json", "docx", "pdf", "client_pdf", "xlsx"}:
            raise Problem(422, "UNSUPPORTED_FORMAT", "Định dạng không hỗ trợ.")
        snapshot, decision = None, None
        if snapshot_id:
            s = db.scalar(select(Snapshot).where(Snapshot.id == snapshot_id, Snapshot.project_id == p.id))
            if not s:
                raise Problem(404, "NOT_FOUND", "Không tìm thấy snapshot.")
            payload = verify_snapshot(s)
            a = db.scalars(select(Approval).where(Approval.snapshot_id == s.id).order_by(Approval.created_at.desc())).first()
            decision = serialize(a, ("project_id",)) if a else None
            snapshot = {"id": s.id, "hash": s.hash, "stage_version": s.stage_version, "created_at": s.created_at, "historical": s.stage_version != p.revision, "current_project_revision": p.revision}
        else:
            payload = snapshot_payload(db, p)
            payload["feedback"] = [serialize(f, ("project_id",)) for f in db.scalars(select(Feedback).where(Feedback.project_id == p.id))]
        paths = {}
        for source_info in payload["sources"]:
            row = source(db, p, source_info["id"])
            paths[source_info["id"]] = source_path(storage, row)
        try:
            data, mime, ext = export_package(payload, format, decision, snapshot, paths)
        except (RuntimeError, ImportError) as e:
            raise Problem(503, "EXPORT_UNAVAILABLE", str(e))
        return Response(data, media_type=mime, headers={"Content-Disposition": f"attachment; filename=stage01-{p.id}-v{payload['project']['revision']}{'-ban-cho-khach' if format == 'client_pdf' else '-5-file-excel' if format == 'xlsx' else ''}.{ext}", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Snapshot-Status": "HISTORICAL" if snapshot and snapshot.get("historical") else "CURRENT" if snapshot else "DRAFT"})

    return app


app = create_app()
