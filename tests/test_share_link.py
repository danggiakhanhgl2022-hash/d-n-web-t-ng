"""Link riêng: khách gửi tệp không cần tài khoản."""
import io
import zipfile

import openpyxl
from fastapi.testclient import TestClient

from conftest import fill_project
from test_xlsx_export import _png


def _public(app):
    return TestClient(app)


def test_client_uploads_through_private_link(api, app):
    project = fill_project(api, api.project())
    r = api.post(f"/projects/{project['id']}/share-link", json={"days": 7})
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    anon = _public(app)
    info = anon.get(f"/api/v1/public/{token}")
    assert info.status_code == 200 and info.json()["files"] == []
    up = anon.post(f"/api/v1/public/{token}/files", data={"note": "Logo của quán", "question_code": "A1"},
                   files={"file": ("logo.png", _png(), "image/png")})
    assert up.status_code == 201, up.text
    assert up.json()["sources"][0]["note"] == "Logo của quán"
    detail = api.get(f"/projects/{project['id']}").json()
    assert detail["sources"][-1]["via"] == "CLIENT_LINK" and detail["sources"][-1]["question_code"] == "A1"
    assert detail["revision"] > project["revision"]
    z = zipfile.ZipFile(io.BytesIO(api.get(f"/projects/{project['id']}/package?format=xlsx").content))
    sheet = openpyxl.load_workbook(io.BytesIO(z.read("04_TU_LIEU_KHACH_GUI.xlsx")))["Tư liệu"]
    assert sheet["F5"].value == "Logo của quán" and sheet["H5"].value == "Khách gửi qua link"


def test_link_rejects_bad_files_and_revocation(api, app):
    project = fill_project(api, api.project())
    token = api.post(f"/projects/{project['id']}/share-link", json={}).json()["token"]
    anon = _public(app)
    bad = anon.post(f"/api/v1/public/{token}/files", files={"file": ("virus.png", b"MZ not an image", "image/png")})
    assert bad.status_code == 422
    exe = anon.post(f"/api/v1/public/{token}/files", files={"file": ("a.exe", b"MZ", "application/octet-stream")})
    assert exe.status_code == 422
    assert anon.get("/api/v1/public/not-a-real-token").status_code == 404
    assert api.client.delete(f"/api/v1/projects/{project['id']}/share-link", headers={"X-CSRF-Token": api.csrf}).status_code == 200
    assert anon.get(f"/api/v1/public/{token}").status_code == 404


def test_new_link_replaces_old_and_anonymous_cannot_create(api, app):
    project = fill_project(api, api.project())
    first = api.post(f"/projects/{project['id']}/share-link", json={}).json()["token"]
    second = api.post(f"/projects/{project['id']}/share-link", json={}).json()["token"]
    anon = _public(app)
    assert anon.get(f"/api/v1/public/{first}").status_code == 404
    assert anon.get(f"/api/v1/public/{second}").status_code == 200
    assert anon.post(f"/api/v1/projects/{project['id']}/share-link", json={}).status_code == 401


def test_client_answers_whole_form_on_web(api, app):
    from conftest import GOOD_ANSWERS
    project = api.project()
    token = api.post(f"/projects/{project['id']}/share-link", json={}).json()["token"]
    anon = _public(app)
    qs = anon.get(f"/api/v1/public/{token}/questions").json()
    codes = {q["code"] for q in qs["questions"]}
    assert "E1" not in codes and "P1" in codes and all(s["id"] != "E" for s in qs["sections"])
    assert anon.put(f"/api/v1/public/{token}/answers/E1", json={"expected_revision": 1, "value": {"x": 1}}).status_code == 403
    early = anon.post(f"/api/v1/public/{token}/submit")
    assert early.status_code == 422 and early.json()["error"]["code"] == "INCOMPLETE"
    for code, value in GOOD_ANSWERS.items():
        if code in codes:
            r = anon.put(f"/api/v1/public/{token}/answers/{code}", json={"expected_revision": 1, "value": value})
            assert r.status_code == 200, (code, r.text)
    view = anon.get(f"/api/v1/public/{token}/project").json()
    assert "approvals" in view and view["id"] == "me" and "status" in view
    assert not any(a["question_code"].startswith("E") for a in view["answers"])
    done = anon.post(f"/api/v1/public/{token}/submit")
    assert done.status_code == 200, done.text
    assert done.json()["submitted_at"]
    staff = api.get(f"/projects/{project['id']}").json()
    assert staff["client_link"]["submitted_at"] and staff["client_link"]["path"] == f"/gui/{token}"


def test_client_can_remove_own_file(api, app):
    project = api.project()
    token = api.post(f"/projects/{project['id']}/share-link", json={}).json()["token"]
    anon = _public(app)
    view = anon.post(f"/api/v1/public/{token}/files", data={"question_code": "A12"}, files={"file": ("nham.png", _png(), "image/png")}).json()
    fid = view["sources"][0]["id"]
    done = anon.delete(f"/api/v1/public/{token}/files/{fid}")
    assert done.status_code == 200 and done.json()["sources"] == []
    assert anon.delete(f"/api/v1/public/{token}/files/{fid}").status_code == 404


def test_uploading_to_text_question_counts_as_answer(api, app):
    project = api.project()
    token = api.post(f"/projects/{project['id']}/share-link", json={}).json()["token"]
    anon = _public(app)
    qs = anon.get(f"/api/v1/public/{token}/questions").json()["questions"]
    b41 = next(q for q in qs if q["code"] == "B4.1")
    assert "tab Tài liệu" not in b41["fields"][0]["example"]
    view = anon.post(f"/api/v1/public/{token}/files", data={"question_code": "B4.1"}, files={"file": ("video-cu.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 64, "video/mp4")})
    assert view.status_code == 201, view.text
    answer = next(a for a in view.json()["answers"] if a["question_code"] == "B4.1")
    assert answer["value"]["link"] == "Đã gửi tệp: video-cu.mp4"


def test_client_starts_alone_and_staff_sees_it(api, app):
    anon = _public(app)
    start = anon.post("/api/v1/public/start")
    assert start.status_code == 201, start.text
    token = start.json()["token"]
    assert start.json()["path"] == f"/gui/{token}"
    assert anon.put(f"/api/v1/public/{token}/answers/A1", json={"expected_revision": 1, "value": {"project": "Khai trương tiệm hoa", "org": "Tiệm hoa Lan"}}).status_code == 200
    items = api.get("/projects").json()["items"]
    row = next(i for i in items if i["name"] == "Khai trương tiệm hoa")
    assert row["customer"] == "Tiệm hoa Lan" and row["client_link"] is True and row["client_submitted_at"] is None


def test_start_is_rate_limited(app):
    anon = _public(app)
    codes = [anon.post("/api/v1/public/start").status_code for _ in range(10)]
    assert codes[:8] == [201] * 8 and codes[8] == 429


def test_staff_can_attach_image_to_a_question_and_remove_it(api):
    project = api.project()
    detail = api.get(f"/projects/{project['id']}").json()
    r = api.post(f"/projects/{project['id']}/sources", data={"expected_revision": detail["revision"], "question_code": "A12", "note": "Logo công ty"},
                 files={"file": ("logo.png", _png(), "image/png")})
    assert r.status_code == 201, r.text
    row = next(s for s in r.json()["sources"] if s["filename"] == "logo.png")
    assert row["question_code"] == "A12" and row["note"] == "Logo công ty"
    gone = api.delete(f"/projects/{project['id']}/sources/{row['id']}?expected_revision={r.json()['revision']}")
    assert gone.status_code == 200 and not any(s["filename"] == "logo.png" for s in gone.json()["sources"])
