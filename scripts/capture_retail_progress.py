"""Capture the Retail scene at known scroll progress, not video timestamps."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/retail-progress'
out.mkdir(parents=True,exist_ok=True)
samples=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
    page.wait_for_selector('input[name=username]',state='visible',timeout=60000)
    page.locator('.cinema-dialog-close').click()
    for n in range(10):
        fraction=n/10
        page.locator('.cinema-chapter').nth(4).evaluate('''(e,f)=>{
          document.documentElement.style.scrollBehavior='auto';
          scrollTo({top:e.getBoundingClientRect().top+scrollY+e.querySelector('.cinema-scene-space').offsetHeight*f,behavior:'instant'});
        }''',fraction)
        page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='retail'",timeout=45000)
        page.wait_for_timeout(950)
        canvas=page.locator('canvas').first
        name=f'progress-{n:02}.png'
        page.screenshot(path=str(out/name))
        samples.append({'fraction':fraction,'timeline':float(canvas.get_attribute('data-timeline')),
                        'clips':json.loads(canvas.get_attribute('data-motion-clips')),'image':name})
    assert not errors,errors
    browser.close()
(out/'samples.json').write_text(json.dumps({'samples':samples,'errors':errors},indent=2),encoding='utf-8')
print('PASS: captured 10 Retail scroll positions; timeline values stored separately from video time')
