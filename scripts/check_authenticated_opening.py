"""An existing session must not bypass the automatic entrance."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out=Path(__file__).resolve().parents[1]/'runtime/verification/authenticated-opening'
out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def api(route):
        path=route.request.url.split('/api/v1')[-1]
        data={'user':{'id':'test','username':'test','display_name':'Test','role':'VIEWER','tenant_id':'test'},'csrf_token':'test'} if path=='/auth/me' else {'items':[],'questions':[],'sections':[]}
        route.fulfill(status=200,json=data)
    page.route('**/api/v1/**',api)
    page.add_init_script('window.entrySamples=[];function record(){const c=document.querySelector("canvas[data-hero-progress]");if(c)entrySamples.push({time:+c.dataset.timeline,rig:+c.dataset.heroProgress});requestAnimationFrame(record)}requestAnimationFrame(record)')
    for attempt in range(2):
        if attempt:page.reload(wait_until='domcontentloaded')
        else:page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
        expect(page.locator('.renaissance-cinema')).to_be_visible()
        page.wait_for_selector('canvas[data-scene=hero]',timeout=15000)
        page.wait_for_timeout(700)
        assert page.locator('.app-shell').count()==0
        assert page.evaluate('scrollY')==0
        page.screenshot(path=str(out/f'entrance-{attempt}.png'))
        expect(page.locator('.app-shell')).to_be_visible(timeout=12000)
        page.wait_for_selector('.renaissance-backdrop canvas[data-scene=hero]',timeout=15000)
        page.wait_for_timeout(1600)
        pose=float(page.locator('.renaissance-backdrop canvas').get_attribute('data-rig-pose'))
        page.locator('.renaissance-backdrop canvas').screenshot(path=str(out/f'workspace-a-{attempt}.png'))
        page.wait_for_timeout(1800)
        moved=float(page.locator('.renaissance-backdrop canvas').get_attribute('data-rig-pose'))
        assert abs(moved-pose)>.005,(pose,moved)
        page.locator('.renaissance-backdrop canvas').screenshot(path=str(out/f'workspace-b-{attempt}.png'))
        samples=page.evaluate('entrySamples')
        assert len(samples)>10 and max(x['rig'] for x in samples)>min(x['rig'] for x in samples),samples
    page.locator('.motion-replay').click()
    expect(page.locator('.renaissance-cinema')).to_be_visible()
    page.wait_for_selector('canvas[data-scene=hero]',timeout=15000)
    expect(page.locator('.app-shell')).to_be_visible(timeout=12000)
    assert not errors,errors
    (out/'checks.json').write_text(json.dumps({'passed':True,'reload_replays':True,'samples':samples,'errors':errors},indent=2))
    browser.close()
print('PASS: existing authenticated session and reload both play moving entrance before workspace; no page errors')
