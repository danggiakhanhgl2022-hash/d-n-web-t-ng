"""Exercise actual row locking/CAS on isolated PostgreSQL; SQLite is not evidence here."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient


def test_two_writers_cannot_commit_the_same_project_revision(api, app):
    if app.state.engine.dialect.name != "postgresql":
        pytest.skip("Requires real isolated PostgreSQL, run scripts/verify_postgres.py")
    project = api.project("QA concurrent revision — isolated database")
    cookies = dict(api.client.cookies)
    headers = {"X-CSRF-Token": api.csrf}
    barrier = Barrier(2)

    def write(code):
        with TestClient(app) as client:
            client.cookies.update(cookies)
            barrier.wait(timeout=10)
            return client.put(f"/api/v1/projects/{project['id']}/answers/{code}", json={
                "expected_revision": project["revision"], "value": f"Concurrent QA {code}",
                "status": "ANSWERED_UNCONFIRMED",
            }, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(write, ["CORE-02", "CORE-03"]))
    assert sorted(results) == [200, 409]
    current = api.get(f"/projects/{project['id']}").json()
    assert current["revision"] == project["revision"] + 1
    assert len(current["answers"]) == 1
    events = api.get(f"/projects/{project['id']}/audit").json()["items"]
    assert sum(event["action"] == "ANSWER_REVISED" for event in events) == 1
