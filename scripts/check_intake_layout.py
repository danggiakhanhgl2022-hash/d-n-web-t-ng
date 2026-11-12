"""Production responsive layout check using the real question catalog and mock project."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / "backend/app/questions.json").read_text(encoding="utf-8"))
sections = catalog["sections"][:9]
ids = {s["id"] for s in sections}
questions = [q for q in catalog["questions"] if q["section"] in ids]
project = dict(id="qa-layout", name="QA Layout", customer="Mock project", revision=1, status="DRAFT", answers=[], sources=[], feedback=[], approvals=[], snapshots=[], stage02={}, validation={
    "required_codes": [q["code"] for q in questions], "active_groups": ["P", "A"], "lite_mode": True,
    "sections": [dict(id=s["id"], applicable=True, total=sum(q["section"] == s["id"] for q in questions), answered=0, confirmed=0) for s in sections],
})
out = root / "runtime/verification"
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    results = []
    for width in (1440, 970, 768, 390):
        page = browser.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        def api(route):
            path = route.request.url.split("/api/v1", 1)[1]
            data = {"user": dict(id="qa", username="qa", display_name="QA", role="ADMIN", tenant_id="qa"), "csrf_token": "qa"} if path == "/auth/me" else {"items": [project]} if path == "/projects" else catalog if path == "/questions" else project if path == "/projects/qa-layout" else {}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        page.route("**/api/v1/**", api)
        page.add_init_script("localStorage.setItem('video-os-project','qa-layout')")
        page.goto("http://127.0.0.1:3100", wait_until="networkidle")
        expect(page.locator(".chapter-stage").first).to_be_visible()
        assert page.locator('.lite-tag').count() == 0
        assert page.locator('.intake-hero .hero-copy > p').count() == 0
        page.locator(".intake-body").scroll_into_view_if_needed()
        page.wait_for_timeout(900)
        sizes = page.evaluate('''() => {
          const rail=document.querySelector('.rail'),stage=document.querySelector('.chapter-stage'),content=document.querySelector('.chapter-content');
          return {viewport:innerWidth,document:document.documentElement.scrollWidth,rail:rail.clientWidth,railScroll:rail.scrollWidth,stage:stage.clientWidth,overlap:stage.getBoundingClientRect().bottom>content.getBoundingClientRect().top+1,art:getComputedStyle(stage).backgroundImage};
        }''')
        assert sizes["document"] <= width, sizes
        assert sizes["railScroll"] <= sizes["rail"] + 1, sizes
        assert not sizes["overlap"], sizes
        assert sizes["stage"] >= min(300, width - 60), sizes
        assert "hero.jpg" in sizes["art"], sizes
        assert not errors, errors
        assert page.locator('.chapter-stage').first.get_attribute('data-art-arrival') is None  # reduced motion
        page.screenshot(path=str(out / f"intake-redesign-{width}.png"))
        page.locator(".rail-item").nth(1).click()
        expect(page.locator(".rail-item").nth(1)).to_have_attribute("aria-current", "step")
        results.append(sizes)
        page.close()
    page = browser.new_page(viewport={"width": 970, "height": 1000})
    page.route("**/api/v1/**", api)
    page.add_init_script("localStorage.setItem('video-os-project','qa-layout')")
    page.goto("http://127.0.0.1:3100", wait_until="networkidle")
    stage = page.locator('.chapter-stage').first
    stage.scroll_into_view_if_needed()
    expect(stage).to_have_attribute('data-art-arrival', 'true')
    page.wait_for_timeout(1100)
    first = stage.evaluate("e=>getComputedStyle(e,'::before').transform")
    page.wait_for_timeout(650)
    second = stage.evaluate("e=>getComputedStyle(e,'::before').transform")
    assert first != second, (first, second)
    for tab in ("sources", "review", "history", "questions"):
        page.locator('.project-tabs button').nth(["questions", "sources", "review", "history"].index(tab)).click()
        page.wait_for_timeout(70)
        assert page.locator('.app-shell').get_attribute('data-view') == tab
        assert page.locator('.workspace').evaluate('e=>e.getAnimations().length') > 0
        page.wait_for_timeout(1000)
        assert page.locator('.workspace').evaluate("e=>getComputedStyle(e).clipPath") == 'none'
    page.close()
    browser.close()
(out / "intake-redesign-checks.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print("PASS: responsive layout; chapter artwork keeps moving; all 4 workspace tabs animate and remove clipping afterwards")
