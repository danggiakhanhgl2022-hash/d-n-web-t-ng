"""Check production UI with intercepted QA data; never deletes customer projects."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(__file__).resolve().parents[1] / "runtime" / "verification"
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
    errors, deleted = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    fixture = {"id": "qa-delete", "name": "QA delete fixture", "customer": "Mock only", "revision": 3, "status": "DRAFT", "client_link": True}
    old = {"id": "qa-old", "name": "QA already deleted", "customer": "Mock only", "revision": 2, "status": "DELETED"}
    def api(route):
        path = route.request.url.split("/api/v1", 1)[1]
        if route.request.method == "DELETE":
            assert path == "/projects/qa-delete"
            assert route.request.post_data_json == {"expected_revision": 3}
            assert route.request.headers["x-csrf-token"] == "qa-csrf"
            deleted.append(path)
            route.fulfill(status=204)
            return
        data = {"user": {"id": "qa-user", "username": "qa", "display_name": "QA", "role": "ADMIN", "tenant_id": "qa"}, "csrf_token": "qa-csrf"} if path == "/auth/me" else {"items": [dict(fixture, status="DELETED") if deleted else fixture, old]} if path == "/projects" else {"questions": [], "sections": []}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
    page.route("**/api/v1/**", api)
    page.goto("http://127.0.0.1:3100", wait_until="networkidle")
    expect(page.get_by_text('QA already deleted')).to_have_count(0)
    expect(page.get_by_text('Khách đang điền')).to_be_visible()
    page.locator('.projects-panel').scroll_into_view_if_needed()
    page.screenshot(path=str(out / 'project-list-softened.png'))
    page.locator(".delete-project").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button").first.click()
    assert not deleted
    page.locator(".delete-project").click()
    page.screenshot(path=str(out / "delete-confirmation.png"))
    page.locator(".delete-confirm").click()
    expect(page.locator(".delete-project")).to_have_count(0)
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert len(deleted) == 1
    page.reload(wait_until="networkidle")
    expect(page.get_by_text('QA delete fixture')).to_have_count(0)
    expect(page.get_by_text('QA already deleted')).to_have_count(0)
    assert not errors, errors
    browser.close()
print("PASS: production UI cancel, confirm, CSRF/revision payload and list removal; API mocked only")
