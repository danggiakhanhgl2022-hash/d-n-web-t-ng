"""Meaningful Stage 01 integration regressions; all approvals use isolated QA fixtures."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from conftest import API, confirm_project, fill_project, latest_snapshot


def test_requires_login(app):
    with TestClient(app) as client:
        assert client.get("/api/v1/projects").status_code == 401


def test_bad_password_does_not_create_session(app):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"username": "owner", "password": "wrong"})
        assert response.status_code == 401
        assert client.get("/api/v1/auth/me").status_code == 401


def test_mutations_require_csrf(api):
    response = api.client.post("/api/v1/projects", json={"name": "CSRF denied", "customer": "QA"})
    assert response.status_code == 403
    assert not api.get("/projects").json()["items"]


def test_logout_revokes_session(api):
    assert api.post("/auth/logout").status_code in (200, 204)
    assert api.get("/auth/me").status_code == 401


def test_catalog_has_entry_core_branch_scene_and_internal_parts(api):
    payload = api.get("/questions").json()
    codes = {q["code"] for q in payload["questions"]}
    assert payload["template_version"] == "3.0.0-stage01"
    assert {"P1", "P2", "P3", "P4"} <= codes and {f"A{n}" for n in range(1, 19)} <= codes
    groups = {q["group"] for q in payload["questions"]}
    assert {f"B{n}" for n in range(1, 8)} | {f"C{n}" for n in range(1, 8)} | {"D", "E"} <= groups
    assert all(q["fields"] for q in payload["questions"])
    assert {s["id"] for s in payload["sections"]} >= {"P", "A-WHO", "D", "E"}


def test_blank_project_has_blockers_and_stage02_closed(api):
    project = api.project()
    assert not project["validation"]["can_submit"]
    assert project["validation"]["blockers"]
    assert not project["stage02"]["allowed"]
    response = api.post(f"/projects/{project['id']}/submit", json={"expected_revision": project["revision"]})
    assert response.status_code in (409, 422)


def test_account_can_edit_but_cannot_confirm_or_approve(api, account):
    project = account.save(account.project(), "C2.1", {"v": "Mục tiêu có thật trong fixture"})
    response = account.post(f"/projects/{project['id']}/confirm", json={"expected_revision": project["revision"], "question_codes": ["C2.1"]})
    assert response.status_code == 403
    response = account.post(f"/projects/{project['id']}/decision", json={"expected_revision": project["revision"], "snapshot_id": "missing", "content_hash": "0" * 64, "decision": "APPROVED", "notes": "forbidden"})
    assert response.status_code == 403
    assert api.get(f"/projects/{project['id']}").json()["answers"][0]["status"] != "CONFIRMED"


def test_viewer_cannot_create_or_edit(api, viewer):
    project = api.project()
    assert viewer.post("/projects", json={"name": "forbidden", "customer": "QA"}).status_code == 403
    assert viewer.put(f"/projects/{project['id']}/answers/C2.1", json={"expected_revision": project["revision"], "value": {"v": "forbidden"}, "status": "ANSWERED_UNCONFIRMED"}).status_code == 403


def test_foreign_tenant_cannot_read_mutate_export_or_handoff(api, app):
    from app.bootstrap import create_owner
    project = api.project()
    create_owner(database_url=app.state.qa_database_url, username="other-owner", password="Other-tenant-password-49!",
                 display_name="Other QA Owner", tenant_name="Other QA Tenant")
    with TestClient(app) as client:
        foreign = API(client).login("other-owner", "Other-tenant-password-49!")
        assert not foreign.get("/projects").json()["items"]
        for suffix in ("", "/audit", "/stage02", "/package?format=json", "/package?format=zip"):
            assert foreign.get(f"/projects/{project['id']}{suffix}").status_code == 404
        assert foreign.put(f"/projects/{project['id']}/answers/C2.1", json={"expected_revision": project["revision"], "value": {"v": "cross tenant write"}, "status": "ANSWERED_UNCONFIRMED"}).status_code == 404


def test_account_cannot_provision_admin(api, account):
    response = account.post("/users", json={"username": "forged-admin", "password": "Forged-admin-test-password!",
                                           "display_name": "forged", "role": "ADMIN"})
    assert response.status_code == 403


@pytest.mark.parametrize("forbidden_status", ["CONFIRMED", "PROPOSED_FROM_SOURCE", "WAIVED_WITH_REASON", "APPROVED"])
def test_client_cannot_forge_confirmation_status(api, forbidden_status):
    project = api.project()
    response = api.put(f"/projects/{project['id']}/answers/C2.1", json={"expected_revision": project["revision"], "value": {"v": "forged"}, "status": forbidden_status, "confirmed_by": api.user["id"]})
    assert response.status_code == 422
    assert api.get(f"/projects/{project['id']}").json()["answers"] == []


def test_stale_editor_cannot_overwrite_newer_answer(api):
    original = api.project()
    current = api.save(original, "C2.1", {"v": "Giá trị mới nhất"})
    response = api.put(f"/projects/{current['id']}/answers/C2.1", json={"expected_revision": original["revision"], "value": {"v": "Giá trị editor cũ"}, "status": "ANSWERED_UNCONFIRMED"})
    assert response.status_code == 409
    actual = api.get(f"/projects/{current['id']}").json()
    assert actual["answers"][0]["value"] == {"v": "Giá trị mới nhất"}


def test_unknown_question_code_rejected(api):
    project = api.project()
    response = api.put(f"/projects/{project['id']}/answers/UNKNOWN-99", json={"expected_revision": project["revision"], "value": "bad", "status": "ANSWERED_UNCONFIRMED"})
    assert response.status_code in (404, 422)


def test_sns_branch_does_not_include_paid_ads_questions(api):
    project = api.save(api.project(), "P3", {"v": ["SNS"]})
    applicable = set(project["validation"]["applicable_codes"])
    assert "C1.1" in applicable
    assert not any(code.startswith("C2.") for code in applicable)


def test_mixed_order_enables_both_branches_and_preserves_hidden_answers(api):
    project = api.save(api.project(), "P3", {"v": ["SNS", "ADS"]})
    applicable = project["validation"]["applicable_codes"]
    assert "C1.1" in applicable and "C2.1" in applicable
    project = api.save(project, "C2.1", {"v": "Lợi thế do PM cung cấp"})
    project = api.save(project, "P3", {"v": ["SNS"]})
    assert "C2.1" not in project["validation"]["applicable_codes"]
    hidden = next(a for a in project["answers"] if a["question_code"] == "C2.1")
    assert hidden["applicable"] is False and hidden["inactive_reason"] == "BRANCH_NOT_APPLICABLE"


def test_client_type_opens_matching_b_branches(api):
    project = api.save(api.project(), "P1", {"v": "FIRST"})
    project = api.save(project, "P2", {"v": ["OLD_VIDEO", "SAMPLE"]})
    project = api.save(project, "P4", {"v": "D3"})
    groups = set(project["validation"]["active_groups"])
    assert {"B1", "B4", "B5", "B6"} <= groups and "B3" not in groups
    assert project["validation"]["lite_mode"] is True
    required = set(project["validation"]["required_codes"])
    assert "A4" not in required and "A3" in required, "Khách lần đầu/gấp chỉ bắt buộc câu ★"
    assert "D1" in required, "Có video cũ cần sửa thì bảng theo cảnh là bắt buộc"


def test_deadline_semantics_not_only_nonempty(api):
    project = api.project()
    response = api.put(f"/projects/{project['id']}/answers/A14", json={"expected_revision": project["revision"], "value": {"preview": "gấp", "final": "ngày mai"}, "status": "ANSWERED_UNCONFIRMED"})
    assert response.status_code == 200
    blockers = response.json()["validation"]["blockers"]
    assert any(b.get("question_code") == "A14" and b["code"] == "INVALID_ANSWER" for b in blockers)
    project = api.save(response.json(), "A14", {"preview": "2030-02-10", "final": "2030-02-01"})
    assert any("trước hoặc cùng ngày" in b["message"] for b in project["validation"]["blockers"])


def test_past_deadline_cannot_be_confirmed(api):
    project = api.save(api.project(), "A14", {"preview": "2020-01-01", "final": "2020-01-02"})
    response = api.post(f"/projects/{project['id']}/confirm", json={"expected_revision": project["revision"], "question_codes": ["A14"]})
    assert response.status_code == 422
    assert "đã qua" in response.text


@pytest.mark.parametrize("count", [0, -1, 1.5])
def test_video_count_must_be_positive_integer(api, count):
    project = api.save(api.project(), "A7", {"count": count, "ratios": ["9:16"]})
    assert any(b.get("question_code") == "A7" for b in project["validation"]["blockers"])


@pytest.mark.parametrize("code,value", [
    ("A7", {"count": None, "ratios": None}),
    ("A7", {"count": "2", "ratios": 42}),
    ("A10", {"tracks": 42}),
    ("A10", {"tracks": {"TEXT": [None], "VOICE": 42, "SUB": "ja"}}),
    ("A12", {"assets": ["LOGO"]}),
    ("D1", {"rows": [None, 42, {"scope": []}]}),
    ("P3", {"v": "SNS"}),
    ("A15", "plain text"),
])
def test_malformed_structured_draft_never_crashes_branch_evaluation(api, code, value):
    project = api.project()
    response = api.put(f"/projects/{project['id']}/answers/{code}", json={"expected_revision": project["revision"], "value": value, "status": "ANSWERED_UNCONFIRMED"})
    assert response.status_code in (200, 422), response.text
    if response.status_code == 200:
        assert not response.json()["validation"]["can_submit"]
        assert any(b.get("question_code") == code for b in response.json()["validation"]["blockers"])
        assert api.get(f"/projects/{project['id']}").status_code == 200
        assert api.post(f"/projects/{project['id']}/validate").status_code == 200
        for fmt in ("pdf", "client_pdf", "docx", "zip"):
            assert api.get(f"/projects/{project['id']}/package?format={fmt}").status_code == 200, fmt


def test_consultation_creates_visible_clarification_and_not_confirmation(api):
    project = api.save(api.project(), "A15", None, status="NEEDS_CONSULTATION")
    assert any(a["question_code"] == "A15" and a["status"] == "NEEDS_CONSULTATION" for a in project["answers"])
    tasks = project["validation"]["blockers"] + project["validation"]["clarifications"]
    assert any(task.get("question_code") == "A15" and task.get("owner_role") == "PM"
               and task.get("code") == "NEEDS_CONSULTATION" for task in tasks)
    response = api.post(f"/projects/{project['id']}/confirm", json={"expected_revision": project["revision"], "question_codes": ["A15"]})
    assert response.status_code in (409, 422)


def test_unconfirmed_answers_cannot_open_gate(api):
    project = fill_project(api, api.project())
    assert not project["validation"]["can_submit"]
    assert not project["stage02"]["allowed"]


def test_authenticated_confirmation_records_actor(api):
    project = api.save(api.project(), "C2.1", {"v": "Nội dung đã được PM xác nhận"})
    project = confirm_project(api, project)
    answer = next(a for a in project["answers"] if a["question_code"] == "C2.1")
    assert answer["status"] == "CONFIRMED"
    assert answer["confirmed_by"] == api.user["id"]
    assert answer["confirmed_at"]


def test_candidate_snapshot_does_not_itself_approve_stage(submitted):
    assert submitted["status"] == "IN_REVIEW"
    assert not submitted["stage02"]["allowed"]
    snapshot = latest_snapshot(submitted)
    assert len(snapshot["hash"]) == 64


def test_approval_rejects_wrong_content_hash(api, submitted):
    snapshot = latest_snapshot(submitted)
    response = api.post(f"/projects/{submitted['id']}/decision", json={"expected_revision": submitted["revision"], "snapshot_id": snapshot["id"], "content_hash": "0" * 64, "decision": "APPROVED", "notes": "wrong hash"})
    assert response.status_code == 409
    assert not api.get(f"/projects/{submitted['id']}").json()["stage02"]["allowed"]


def test_approval_opens_only_handoff_and_records_real_actor(api, approved):
    assert approved["status"] == "APPROVED"
    assert approved["stage02"]["allowed"]
    handoff = api.get(f"/projects/{approved['id']}/stage02").json()
    assert handoff["allowed"]
    assert approved["approvals"]
    event = approved["approvals"][-1]
    assert (event.get("actor_id") or event.get("reviewer_id")) == api.user["id"]


def test_edit_after_approval_closes_handoff_preserves_history(api, approved):
    old_snapshots = approved["snapshots"]
    project = api.save(approved, "C2.1", {"v": "Mục tiêu thay đổi cần duyệt lại"})
    assert project["status"] == "STALE"
    assert not project["stage02"]["allowed"]
    assert project["approvals"] == approved["approvals"]
    # Liveness labels may change; immutable snapshot identity/content may not.
    stable_fields = ("id", "hash", "stage_version", "created_at")
    assert [{k: s.get(k) for k in stable_fields} for s in project["snapshots"]] == [
        {k: s.get(k) for k in stable_fields} for s in old_snapshots
    ]
    assert not api.get(f"/projects/{project['id']}/stage02").json()["allowed"]


def test_feedback_does_not_forge_approval(api, submitted):
    response = api.post(f"/projects/{submitted['id']}/feedback", json={"expected_revision": submitted["revision"], "message": "Cần diễn đạt rõ hơn"})
    assert response.status_code == 200, response.text
    assert response.json()["feedback"]
    assert not response.json()["stage02"]["allowed"]


def test_changes_requested_has_explicit_event_and_blocks_handoff(api, submitted):
    snapshot = latest_snapshot(submitted)
    response = api.post(f"/projects/{submitted['id']}/decision", json={"expected_revision": submitted["revision"], "snapshot_id": snapshot["id"], "content_hash": snapshot["hash"], "decision": "CHANGES_REQUESTED", "notes": "QA request: revise deadline"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CHANGES_REQUESTED"
    assert not response.json()["stage02"]["allowed"]


def test_approve_with_stale_revision_rejected(api, submitted):
    snapshot = latest_snapshot(submitted)
    current = api.save(submitted, "C2.1", {"v": "Changed while reviewer was reading"})
    response = api.post(f"/projects/{submitted['id']}/decision", json={"expected_revision": submitted["revision"], "snapshot_id": snapshot["id"], "content_hash": snapshot["hash"], "decision": "APPROVED", "notes": "stale"})
    assert response.status_code == 409
    assert not current["stage02"]["allowed"]


def upload(api, project, filename="brief.txt", content=b"C2.1: Training objective from source", content_type="text/plain"):
    response = api.post(f"/projects/{project['id']}/sources", data={"expected_revision": project["revision"]}, files={"file": (filename, content, content_type)})
    return response


def test_prefill_only_proposes_with_source_evidence(api):
    project = api.project()
    response = upload(api, project)
    assert response.status_code in (200, 201), response.text
    project = response.json()
    source = project["sources"][-1]
    response = api.post(f"/projects/{project['id']}/prefill", json={"expected_revision": project["revision"], "source_id": source["id"]})
    assert response.status_code == 200, response.text
    answer = next(a for a in response.json()["answers"] if a["question_code"] == "C2.1")
    assert answer["status"] == "PROPOSED_FROM_SOURCE"
    assert answer["source_id"] == source["id"]
    assert answer["evidence_locator"]
    assert not answer["confirmed_by"]


def test_prefill_conflict_does_not_silently_replace_confirmed_value(api):
    project = confirm_project(api, api.save(api.project(), "C2.1", {"v": "Confirmed original objective"}))
    response = upload(api, project)
    assert response.status_code in (200, 201), response.text
    project = response.json()
    response = api.post(f"/projects/{project['id']}/prefill", json={"expected_revision": project["revision"], "source_id": project["sources"][-1]["id"]})
    assert response.status_code == 200, response.text
    detail = response.json()
    answer = next(a for a in detail["answers"] if a["question_code"] == "C2.1")
    assert answer["status"] == "CONFLICTED"
    audit = api.get(f"/projects/{project['id']}/audit").json()
    assert "Confirmed original objective" in json.dumps(audit, ensure_ascii=False)


@pytest.mark.parametrize("filename,content,content_type", [
    ("payload.exe", b"MZnot-a-document", "application/octet-stream"),
    ("payload.zip", b"PKnot-a-document", "application/zip"),
    ("fake.pdf", b"not a pdf", "application/pdf"),
    ("fake.docx", b"not a docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
])
def test_rejects_unsupported_or_spoofed_sources(api, filename, content, content_type):
    project = api.project()
    response = upload(api, project, filename, content, content_type)
    assert response.status_code in (400, 413, 415, 422), response.text
    assert not api.get(f"/projects/{project['id']}").json()["sources"]


def test_uploaded_client_filename_never_becomes_storage_path(api):
    project = api.project()
    response = upload(api, project, "../../escape.txt", b"Safe fixture text")
    if response.status_code in (200, 201):
        project = response.json()
        source = project["sources"][-1]
        download = api.get(f"/projects/{project['id']}/sources/{source['id']}/download")
        assert download.status_code == 200
        assert download.content == b"Safe fixture text"
        assert "../" not in download.headers.get("content-disposition", "")
    else:
        assert response.status_code in (400, 415, 422)


def test_scan_pdf_has_explicit_manual_fallback(api):
    from pypdf import PdfWriter
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(output)
    response = upload(api, api.project(), "scan.pdf", output.getvalue(), "application/pdf")
    assert response.status_code in (200, 201), response.text
    source = response.json()["sources"][-1]
    assert any(term in json.dumps(source).upper() for term in ("MANUAL", "NO_TEXT", "OCR", "UNEXTRACTABLE")), source


def test_docx_extracts_text_but_does_not_confirm(api):
    from docx import Document
    buffer = io.BytesIO()
    document = Document()
    document.add_paragraph("C2.1: Nội dung trích từ DOCX chỉ là đề xuất")
    document.save(buffer)
    original = buffer.getvalue()
    response = upload(api, api.project(), "fixture.docx", original,
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert response.status_code in (200, 201), response.text
    project = response.json()
    source = project["sources"][-1]
    assert source["sha256"] == hashlib.sha256(original).hexdigest()
    assert "C2.1" in source["extracted_text"]
    assert not project["answers"], "Uploading must not implicitly answer or confirm anything"
    response = api.post(f"/projects/{project['id']}/prefill", json={"expected_revision": project["revision"], "source_id": source["id"]})
    assert response.status_code == 200
    answer = next(a for a in response.json()["answers"] if a["question_code"] == "C2.1")
    assert answer["status"] == "PROPOSED_FROM_SOURCE"


def test_oversized_source_rejected_without_record(api):
    project = api.project()
    response = upload(api, project, "large.txt", b"x" * (10 * 1024 * 1024 + 1))
    assert response.status_code == 413
    assert not api.get(f"/projects/{project['id']}").json()["sources"]


def test_draft_package_is_real_zip_and_cannot_be_mistaken_for_approval(api):
    project = api.project()
    response = api.get(f"/projects/{project['id']}/package?format=zip")
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        for folder in ("INPUT", "WORK", "OUTPUT", "REVIEW", "APPROVAL", "SNAPSHOT"):
            assert any(f"{folder}/" in name for name in names), folder
        text = "\n".join(archive.read(name).decode("utf-8", errors="replace") for name in names if name.endswith((".md", ".json")))
        assert "DRAFT" in text or "NHÁP" in text
        assert "PENDING" in text


def test_package_manifest_checksums_match_actual_zip_bytes(api, approved):
    snapshot = latest_snapshot(approved)
    response = api.get(f"/projects/{approved['id']}/package?format=zip&snapshot_id={snapshot['id']}")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest_path = next(name for name in archive.namelist() if name.endswith("/stage_manifest.json"))
        prefix = manifest_path.removesuffix("stage_manifest.json")
        manifest = json.loads(archive.read(manifest_path))
        assert manifest["artifacts"]
        assert manifest["approval"]["decision"] == "APPROVED"
        for artifact in manifest["artifacts"]:
            payload = archive.read(prefix + artifact["path"])
            assert artifact["sha256"] == hashlib.sha256(payload).hexdigest()
            assert artifact["size"] == len(payload)


def test_source_tampering_cannot_be_downloaded_as_verified_original(api, app):
    from pathlib import Path
    from sqlalchemy import select
    from app.models import Source
    project = api.project()
    response = upload(api, project, "tamper-check.txt", b"C2.1: Original source bytes")
    assert response.status_code in (200, 201), response.text
    project = response.json()
    source = project["sources"][-1]
    with app.state.session_factory() as session:
        record = session.scalar(select(Source).where(Source.id == source["id"]))
        storage_name = record.storage_name
    stored = Path(app.state.storage_dir) / storage_name
    assert stored.is_file(), "Fixture needs actual retained original file"
    stored.write_bytes(b"C2.1: Corrupted bytes after original upload")
    response = api.get(f"/projects/{project['id']}/sources/{source['id']}/download")
    assert response.status_code in (409, 422), response.text
    response = api.post(f"/projects/{project['id']}/prefill", json={"expected_revision": project["revision"], "source_id": source["id"]})
    assert response.status_code in (409, 422), response.text


def test_snapshot_json_export_preserves_immutable_payload_after_project_edit(api, approved):
    snapshot = latest_snapshot(approved)
    url = f"/projects/{approved['id']}/package?format=json&snapshot_id={snapshot['id']}"
    before = api.get(url)
    assert before.status_code == 200
    api.save(approved, "C2.1", {"v": "New goal not yet approved"})
    after = api.get(url)
    assert after.status_code == 200
    # Export metadata should flag an old snapshot as historical; signed content stays frozen.
    first, second = before.json(), after.json()
    for field in ("payload", "approval", "delivery_matrix"):
        assert first[field] == second[field]
    for field in ("id", "hash", "stage_version", "created_at"):
        assert first["snapshot"].get(field) == second["snapshot"].get(field)
    assert second["snapshot"]["historical"] is True


@pytest.mark.parametrize("fmt,magic", [("docx", b"PK"), ("pdf", b"%PDF-")])
def test_document_exports_are_actual_documents(api, approved, fmt, magic):
    snapshot = latest_snapshot(approved)
    response = api.get(f"/projects/{approved['id']}/package?format={fmt}&snapshot_id={snapshot['id']}")
    assert response.status_code == 200, response.text
    assert response.content.startswith(magic)
    assert len(response.content) > 500
    if fmt == "docx":
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert "word/document.xml" in archive.namelist()
    else:
        from pypdf import PdfReader
        assert len(PdfReader(io.BytesIO(response.content)).pages) > 0


def test_audit_keeps_revisions_and_never_password_or_session_secret(api):
    project = api.save(api.project(), "C2.1", {"v": "First revision"})
    project = api.save(project, "C2.1", {"v": "Second revision"})
    response = api.get(f"/projects/{project['id']}/audit")
    assert response.status_code == 200
    text = json.dumps(response.json(), ensure_ascii=False)
    assert "First revision" in text and "Second revision" in text
    assert "Stage01-test-password-37!" not in text
    assert api.csrf not in text
