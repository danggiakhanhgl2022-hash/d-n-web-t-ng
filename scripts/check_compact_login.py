"""Check compact login sizing and reachable controls on short screens."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out=Path(__file__).resolve().parents[1]/'runtime/verification/compact-login'
out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width,height in [(1440,900),(390,844),(320,520)]:
        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.route('**/api/v1/auth/me',lambda route:route.fulfill(status=401,json={'error':'unauthenticated'}))
        page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
        dialog=page.locator('.cinema-login-dialog')
        expect(dialog).to_be_visible(timeout=30000)
        page.wait_for_function("['ready','fallback'].includes(document.querySelector('.renaissance-cinema').dataset.status)",timeout=30000)
        bounds=dialog.bounding_box()
        assert bounds and bounds['width']<=280 and bounds['height']<=height-20,(width,height,bounds)
        assert abs(bounds['x']+bounds['width']/2-width/2)<2,(width,bounds)
        assert dialog.evaluate("e=>getComputedStyle(e,'::backdrop').backdropFilter")=='none'
        assert dialog.locator('.login-panel').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(16, 23, 17)'
        page.locator('input[name=username]').fill('qa')
        page.locator('input[name=password]').fill('test-password')
        button=dialog.locator('button[type=submit],form button:not([type])')
        button.scroll_into_view_if_needed();expect(button).to_be_visible()
        assert button.evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(243, 62, 170)'
        page.screenshot(path=str(out/f'login-{width}x{height}.png'))
        page.keyboard.press('Escape');expect(dialog).not_to_be_visible()
        assert not errors,errors
        page.close()
    browser.close()
print('PASS: compact centered login; inputs and button reachable; Escape closes at desktop and short/mobile sizes')
