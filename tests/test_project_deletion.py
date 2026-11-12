"""Project removal must not bypass revisions, access control or evidence retention."""
from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import API


def remove(api, project, csrf=True, revision=None):
    return api.client.request("DELETE", f"/api/v1/projects/{project['id']}",
        headers={"X-CSRF-Token": api.csrf} if csrf else {},
        json={"expected_revision": project["revision"] if revision is None else revision})


def test_delete_hides_project_and_all_saved_routes_but_retains_evidence(api, app):
    from app.models import Project, Answer, AuditEvent
    project = api.save(api.project(), "P1", {"v": "FEW"})
    assert remove(api, project).status_code == 204
    assert not api.get("/projects").json()["items"]
    for suffix in ("", "/audit", "/stage02", "/package?format=json"):
        assert api.get(f"/projects/{project['id']}{suffix}").status_code == 404
    assert api.put(f"/projects/{project['id']}/answers/P1", json={
        "expected_revision": project["revision"] + 1, "value": {"v": "MANY"}}).status_code == 404
    assert remove(api, project).status_code == 404
    with app.state.session_factory() as db:
        stored = db.get(Project, project["id"])
        assert stored.status == "DELETED"
        assert stored.revision == project["revision"] + 1
        assert db.scalar(select(Answer).where(Answer.project_id == project["id"]))
        event = db.scalar(select(AuditEvent).where(AuditEvent.project_id == project["id"], AuditEvent.action == "PROJECT_DELETED"))
        assert event is not None


def test_delete_rejects_missing_csrf_stale_revision_and_viewer(api, viewer):
    project = api.project()
    assert remove(api, project, csrf=False).status_code == 403
    assert remove(viewer, project).status_code == 403
    updated = api.save(project, "P1", {"v": "FEW"})
    assert remove(api, project).status_code == 409
    assert api.get(f"/projects/{project['id']}").status_code == 200
    assert remove(api, updated).status_code == 204


def test_deleted_project_revokes_public_link_and_stays_hidden_after_reload(api, app):
    project = api.project()
    shared = api.post(f"/projects/{project['id']}/share-link", json={"days": 7})
    assert shared.status_code == 201
    token = shared.json()['token']
    with TestClient(app) as visitor:
        assert visitor.get(f'/api/v1/public/{token}/project').status_code == 200
        assert remove(api, project).status_code == 204
        assert visitor.get(f'/api/v1/public/{token}/project').status_code == 404
    assert all(item['id'] != project['id'] for item in api.get('/projects').json()['items'])


def test_account_can_delete_and_foreign_tenant_cannot(api, account, app):
    from app.bootstrap import create_owner
    project = account.project()
    create_owner(database_url=app.state.qa_database_url, username="foreign-delete",
        password="Foreign-delete-password-49!", display_name="Other Owner", tenant_name="Other Tenant")
    with TestClient(app) as client:
        foreign = API(client).login("foreign-delete", "Foreign-delete-password-49!")
        assert remove(foreign, project).status_code == 404
    assert remove(account, project).status_code == 204
