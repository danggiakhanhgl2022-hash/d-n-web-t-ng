"""Audit that all hero tracks are retained and reassemble to the same poses."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/hero-parts'
out.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:3100/?motionAudit=1',wait_until='domcontentloaded')
    page.wait_for_selector('canvas[data-hero-parts]',timeout=60000)
    report=json.loads(page.locator('canvas').get_attribute('data-hero-parts'))
    assert not report['unresolved'],report
    assert sum(report['parts'].values())==report['sourceTracks']==552,report
    for name in ('woman.body-and-rig','woman.right-hand','woman.left-hand','woman.skateboard','woman.cup','man.body-and-rig','man.right-hand','man.left-hand','man.bag-1','man.bag-2'):
        assert report['parts'].get(name,0)>0,(name,report)
    assert report['audit']['maximumTransformDifference']<1e-6,report
    page.wait_for_selector('input[name=username]',state='visible',timeout=15000)
    assert not errors,errors
    browser.close()
(out/'checks.json').write_text(json.dumps({'report':report,'errors':errors},indent=2),encoding='utf-8')
print('PASS: 552 tracks retained; separated actions match the source at seven poses; login appears')
