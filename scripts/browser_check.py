"""Live browser acceptance against an explicitly isolated QA database/server.

Requires STAGE01_BROWSER_QA=1 and a running test backend on 8100 + UI on3100.
All project creation and approvals below belong to the QA tenant only.
"""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import sys
import time
import zipfile

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from conftest import GOOD_CORE


def main():
    if os.getenv("STAGE01_BROWSER_QA") != "1":
        raise SystemExit("Refusing browser write tests without STAGE01_BROWSER_QA=1 and isolated QA server.")
    out = ROOT / "runtime" / "browser-qa"
    out.mkdir(parents=True, exist_ok=True)
    results, browser_errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = context.new_page()
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        page.goto("http://127.0.0.1:3100", wait_until="networkidle")
        page.wait_for_timeout(1500)
        entry=page.locator('#login-form').bounding_box()
        assert entry and abs(entry['x']+entry['width']/2-720)<20 and entry['y']>=0 and entry['y']+entry['height']<=1000,entry
        assert entry['height']<680 and abs(entry['y']+entry['height']/2-500)<25,entry
        page.screenshot(path=str(out / "01-login.png"), full_page=False)
        results.append("Login form centered and entirely visible in first viewport")
        page.get_by_label("Tài khoản", exact=True).fill("qa-browser-owner")
        page.get_by_label("Mật khẩu", exact=True).fill(os.environ["STAGE01_BROWSER_PASSWORD"])
        page.get_by_role("button", name="Vào không gian làm việc", exact=False).click()
        expect(page.get_by_role("button", name="Tạo dự án", exact=True)).to_be_visible(timeout=20000)
        assert page.locator('.renaissance-cinema').count()==0
        assert page.locator('.workspace-transition').count()==1
        results.append("Browser login with cookie session")
        page.get_by_role("button", name="Tạo dự án", exact=True).click()
        page.get_by_label("Tên dự án / chiến dịch", exact=False).fill("QA CHẶNG A — KHÔNG PHẢI KHÁCH HÀNG")
        page.get_by_label("Khách hàng / đơn vị yêu cầu", exact=False).fill("QA DEMO isolated database")
        page.get_by_role("button", name="Tạo & bắt đầu", exact=False).click()
        card = page.locator('[data-question-code="CORE-02"]')
        expect(card).to_be_visible()
        card.locator("textarea").first.fill(GOOD_CORE["CORE-02"])
        with page.expect_response(lambda response: response.url.endswith("/answers/CORE-02") and response.request.method == "PUT") as saved:
            card.get_by_role("button", name="Lưu câu trả lời", exact=True).click()
        assert saved.value.status == 200
        results.append("Saved an answer through the actual questionnaire form")
        if page.locator(".renaissance-backdrop").count():
            contrast = page.evaluate('''() => {
                const input=document.querySelector('.question-card textarea');
                const heading=document.querySelector('.question-heading h3');
                const rgb=value=>value.match(/[\\d.]+/g).slice(0,3).map(Number);
                const luminance=values=>values.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
                const ratio=(a,b)=>{const x=luminance(rgb(a)),y=luminance(rgb(b));return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
                const css=getComputedStyle(input),placeholder=getComputedStyle(input,'::placeholder');
                return {inputSize:parseFloat(css.fontSize),headingSize:parseFloat(getComputedStyle(heading).fontSize),textContrast:ratio(css.color,css.backgroundColor),placeholderContrast:ratio(placeholder.color,css.backgroundColor)};
            }''')
            assert contrast["inputSize"] >= 16 and contrast["headingSize"] >= 20, contrast
            assert contrast["textContrast"] >= 4.5 and contrast["placeholderContrast"] >= 4.5, contrast
            results.append("Renaissance input text and placeholder meet 4.5:1 contrast; readable font sizes")
        page.wait_for_timeout(1300)
        page.evaluate("window.scrollTo(0,0)")
        page.screenshot(path=str(out / "02-questionnaire.png"), full_page=True)
        project_id = page.evaluate("localStorage.getItem('video-os-project')")
        assert project_id
        me = context.request.get("http://127.0.0.1:3100/api/v1/auth/me").json()
        assert me["user"]["username"] == "qa-browser-owner"
        headers = {"X-CSRF-Token": me["csrf_token"]}

        def get_project():
            response = context.request.get(f"http://127.0.0.1:3100/api/v1/projects/{project_id}")
            assert response.ok, response.text()
            return response.json()

        def mutate(suffix, body):
            url = f"http://127.0.0.1:3100/api/v1/projects/{project_id}{suffix}"
            response = context.request.put(url, data=body, headers=headers) if suffix.startswith("/answers/") else context.request.post(url, data=body, headers=headers)
            assert response.ok, response.text()
            return response.json()

        project = get_project()
        assert not project["stage02"]["allowed"]
        page.get_by_role("button", name="Tài liệu nguồn", exact=False).first.click()
        page.wait_for_function("document.querySelector('.workspace-transition')?.dataset.transitionKey.includes(':sources:')")
        assert page.locator('.workspace-transition').evaluate("el=>el.getAnimations().some(a=>a.playState==='running')")
        page.wait_for_timeout(950)
        assert float(page.locator('.workspace-transition').evaluate("el=>getComputedStyle(el).opacity"))<.01
        results.append("Page navigation starts a real transition animation and clears it after entry")
        page.get_by_label("Chọn tài liệu nguồn", exact=True).set_input_files({
            "name": "qa-evidence.txt", "mimeType": "text/plain",
            "buffer": ("CORE-10: " + GOOD_CORE["CORE-10"]).encode("utf-8"),
        })
        page.get_by_role("button", name="Tải tài liệu lên", exact=True).click()
        expect(page.get_by_role("heading", name="qa-evidence.txt", exact=True)).to_be_visible()
        with page.expect_response(lambda response: response.url.endswith("/prefill") and response.request.method == "POST") as suggested:
            page.get_by_role("button", name="Gợi ý điền từ nguồn", exact=True).click()
        assert suggested.value.status == 200
        project = get_project()
        proposal = next(a for a in project["answers"] if a["question_code"] == "CORE-10")
        assert proposal["status"] == "PROPOSED_FROM_SOURCE" and proposal["source_id"]
        results.append("Uploaded source through UI; explicit-marker prefill kept evidence and remained unconfirmed")
        # API writes use the same browser session. UI review/approval and downloads follow.
        for code, value in GOOD_CORE.items():
            project = mutate(f"/answers/{code}", {"expected_revision": project["revision"], "value": value,
                                                  "status": "ANSWERED_UNCONFIRMED"})
        assert all(a["status"] != "CONFIRMED" for a in project["answers"])
        results.append("Saved all structured fields without auto-confirmation; handoff blocked")
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Kiểm tra & gửi", exact=False).first.click()
        page.get_by_role("button", name="Xác nhận câu trả lời chung", exact=False).click()
        expect(page.get_by_role("button", name="Gửi thông tin để duyệt", exact=False)).to_be_enabled(timeout=10000)
        page.get_by_role("button", name="Gửi thông tin để duyệt", exact=False).click()
        expect(page.get_by_role("button", name="Xác nhận phiên bản này", exact=False)).to_be_visible(timeout=10000)
        page.wait_for_timeout(1300)
        page.screenshot(path=str(out / "03-review.png"), full_page=True)
        page.get_by_role("button", name="Xác nhận phiên bản này", exact=False).click()
        expect(page.get_by_text("Đủ điều kiện chuyển giao", exact=False)).to_be_visible(timeout=10000)
        approved = get_project()
        assert approved["status"] == "APPROVED" and approved["stage02"]["allowed"]
        assert approved["approvals"][-1]["actor_id"] == me["user"]["id"]
        results.append("Human QA reviewer confirmed and approved exact snapshot via UI; handoff opened")
        page.screenshot(path=str(out / "04-approved.png"), full_page=True)
        approved_snapshot = approved["snapshots"][-1]["id"]
        for fmt in ["zip", "json", "docx", "pdf"]:
            response = context.request.get(f"http://127.0.0.1:3100/api/v1/projects/{project_id}/package?format={fmt}&snapshot_id={approved_snapshot}")
            assert response.ok, response.text()
            content = response.body()
            assert len(content) > 100
            (out / f"qa-information-package.{fmt}").write_bytes(content)
            if fmt == "zip":
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    assert any("FOLDER_THONG_TIN" in name for name in archive.namelist())
            elif fmt == "pdf":
                assert content.startswith(b"%PDF")
            elif fmt == "docx":
                assert content.startswith(b"PK")
        results.append("Authenticated ZIP/JSON/DOCX/PDF downloads are actual parseable artifacts")
        revised = mutate("/answers/CORE-02", {"expected_revision": approved["revision"], "value": "QA fixture revised after approval",
                                              "status": "ANSWERED_UNCONFIRMED"})
        assert revised["status"] == "STALE" and not revised["stage02"]["allowed"]
        assert revised["snapshots"] and revised["approvals"]
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Kiểm tra & gửi", exact=False).first.click()
        expect(page.get_by_text("Giai đoạn 02 đang khóa", exact=False)).to_be_visible()
        results.append("Revision after approval keeps immutable history and closes handoff")
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(out / "05-mobile.png"), full_page=True)
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
        assert not overflow, "Mobile horizontal overflow"
        assert not browser_errors, browser_errors
        results.append("Responsive mobile layout; no browser runtime errors")
        browser.close()
    (out / "result.json").write_text(json.dumps({"status": "PASS", "database": "isolated QA only", "checks": results,
                                                "browser_errors": browser_errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "checks": results, "artifacts": "runtime/browser-qa"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
