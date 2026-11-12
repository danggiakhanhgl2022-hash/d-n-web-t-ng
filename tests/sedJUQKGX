"""Isolated Stage 01 API fixtures. No customer files or production approvals."""
from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class API:
    def __init__(self, client: TestClient):
        self.client = client
        self.csrf = None
        self.user = None

    def login(self, username="owner", password="Stage01-test-password-37!"):
        response = self.client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        self.csrf = response.json()["csrf_token"]
        self.user = response.json()["user"]
        return self

    def get(self, path, **kwargs):
        return self.client.get("/api/v1" + path, **kwargs)

    def post(self, path, **kwargs):
        headers = kwargs.pop("headers", {})
        return self.client.post("/api/v1" + path, headers={"X-CSRF-Token": self.csrf or "", **headers}, **kwargs)

    def put(self, path, **kwargs):
        headers = kwargs.pop("headers", {})
        return self.client.put("/api/v1" + path, headers={"X-CSRF-Token": self.csrf or "", **headers}, **kwargs)

    def delete(self, path, **kwargs):
        headers = kwargs.pop("headers", {})
        return self.client.delete("/api/v1" + path, headers={"X-CSRF-Token": self.csrf or "", **headers}, **kwargs)

    def project(self, name="QA FIXTURE — not customer data"):
        response = self.post("/projects", json={"name": name, "customer": "QA DEMO ONLY"})
        assert response.status_code in (200, 201), response.text
        return response.json()

    def save(self, project, code, value, **extra):
        response = self.put(f"/projects/{project['id']}/answers/{code}", json={
            "expected_revision": project["revision"], "value": value,
            "status": "ANSWERED_UNCONFIRMED", **extra,
        })
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture
def app(tmp_path):
    from app.main import create_app
    from app.bootstrap import create_owner

    override = os.getenv("STAGE01_TEST_DATABASE_URL")
    database_url = override or "sqlite:///" + (tmp_path / "stage01-test.sqlite3").as_posix()
    if override:
        from sqlalchemy.engine import make_url
        from app.db import Base, make_engine
        parsed = make_url(override)
        database_name = parsed.database or ""
        if not (database_name.startswith("test_") or database_name.endswith("_tests")):
            raise RuntimeError("Refusing destructive QA setup: database name must start test_ or end _tests")
        # Only the explicitly isolated test database may have its tables reset.
        setup_engine = make_engine(override)
        try:
            Base.metadata.drop_all(setup_engine)
            Base.metadata.create_all(setup_engine)
        finally:
            setup_engine.dispose()
    application = create_app(database_url=database_url, storage_dir=str(tmp_path / "storage"))
    application.state.qa_database_url = database_url
    # create_owner must create a tenant + authenticated administrator, never auto-confirm answers.
    with TestClient(application) as client:
        create_owner(database_url=database_url, username="owner", password="Stage01-test-password-37!",
                     display_name="QA Owner", tenant_name="QA Tenant")
        yield application
    application.state.engine.dispose()


@pytest.fixture
def api(app):
    with TestClient(app) as client:
        yield API(client).login()


@pytest.fixture
def account(api, app):
    response = api.post("/users", json={"username": "account", "password": "Stage01-account-password!",
                                       "display_name": "QA Account", "role": "ACCOUNT"})
    assert response.status_code in (200, 201), response.text
    with TestClient(app) as client:
        yield API(client).login("account", "Stage01-account-password!")


@pytest.fixture
def viewer(api, app):
    response = api.post("/users", json={"username": "viewer", "password": "Stage01-viewer-password!",
                                       "display_name": "QA Viewer", "role": "VIEWER"})
    assert response.status_code in (200, 201), response.text
    with TestClient(app) as client:
        yield API(client).login("viewer", "Stage01-viewer-password!")


GOOD_ANSWERS = {
 "P1": {"v": "FEW"}, "P2": {"v": ["IDEA"]}, "P3": {"v": ["SNS"]}, "P4": {"v": "LATER"},
 "A1": {"project": "Khai trương chi nhánh 2", "org": "Quán QA (dữ liệu thử)"},
 "A2": {"name": "QA Owner", "channel": "EMAIL", "contact": "qa@example.invalid"},
 "A3": {"v": "EVENT"}, "A4": {"age": "18–30", "gender": "ALL", "area": "Pleiku"},
 "A5": {"v": ["PRICE", "PROMO"]},
 "A6": {"action": "CONTACT", "exact": "0901 234 567"},
 "A7": {"count": 2, "ratios": ["9:16"]},
 "A8": {"length": "S15_30", "strict": "FLEX"},
 "A9": {"where": ["TIKTOK", "META"], "main": "TikTok"},
 "A10": {"tracks": {"TEXT": ["VI"], "VOICE": ["NONE"], "SUB": ["NONE"]}, "other_lang": ""},
 "A11": {"mood": ["FUN"], "links": "", "like": "", "dislike": ""},
 "A12": {"assets": {"LOGO": "HAVE", "PRODUCT": "HAVE", "SCRIPT": "NEW", "BRAND": "NO", "MUSIC": "NO", "VOICE": "NO"}},
 "A13": {"_na": True},
 "A14": {"preview": "2030-01-10", "final": "2030-01-12", "publish": "2030-01-15"},
 "A15": {"range": "R2"},
 "A16": {"name": "QA Owner", "mode": "ONE"},
 "A17": {"v": "NO"},
 "A18": {"owner": "OWN", "proof": ""},
 "C1.1": {"v": "OFFER"}, "C1.2": {"series": "SINGLE", "previous": ""}, "C1.3": {"v": ["CAPTION"]},
 "E1": {"v": ["1080x1920"]}, "E2": {"v": "EACH_RATIO"},
 "E10": {"status": "VERIFIED", "evidence": "Ảnh và logo do khách tự sở hữu (QA)"},
 "E11": {"amount": 8000000, "rounds": 2},
}
# Tên cũ giữ cho các test cũ còn tham chiếu.
GOOD_CORE = GOOD_ANSWERS


def fill_project(api, project):
    import copy
    for code, value in GOOD_ANSWERS.items():
        project = api.save(project, code, copy.deepcopy(value))
    required = set(project["validation"]["required_codes"])
    assert required <= set(GOOD_ANSWERS), sorted(required - set(GOOD_ANSWERS))
    return project


def confirm_project(api, project):
    codes = [a["question_code"] for a in project["answers"] if a["status"] == "ANSWERED_UNCONFIRMED"]
    response = api.post(f"/projects/{project['id']}/confirm", json={"expected_revision": project["revision"], "question_codes": codes})
    assert response.status_code == 200, response.text
    return response.json()


def submit_project(api, project):
    response = api.post(f"/projects/{project['id']}/submit", json={"expected_revision": project["revision"]})
    assert response.status_code == 200, response.text
    return response.json()


def latest_snapshot(project):
    return project["snapshots"][-1]


@pytest.fixture
def confirmed(api):
    return confirm_project(api, fill_project(api, api.project()))


@pytest.fixture
def submitted(api, confirmed):
    return submit_project(api, confirmed)


@pytest.fixture
def approved(api, submitted):
    snapshot = latest_snapshot(submitted)
    response = api.post(f"/projects/{submitted['id']}/decision", json={
        "expected_revision": submitted["revision"], "snapshot_id": snapshot["id"],
        "content_hash": snapshot["hash"], "decision": "APPROVED", "notes": "QA fixture approval, isolated test DB only",
    })
    assert response.status_code == 200, response.text
    return response.json()
