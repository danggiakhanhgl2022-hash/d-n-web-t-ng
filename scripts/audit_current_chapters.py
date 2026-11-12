"""Record each current chapter after explicitly dismissing automatic login."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
out=root/'runtime/verification/current-chapter-audit';out.mkdir(parents=True,exist_ok=True)
scenes=json.loads((root/'frontend/public/renaissance/3d/scenes.json').read_text(encoding='utf-8'))
rows=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 page=browser.new_page(viewport={'width':1280,'height':800})
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
 page.wait_for_selector('input[name=username]',state='visible',timeout=30000)
 page.locator('.cinema-dialog-close').click()
 for i,scene in enumerate(scenes):
  page.locator('.cinema-chapter').nth(i).evaluate("e=>{document.documentElement.style.scrollBehavior='auto';scrollTo({top:e.getBoundingClientRect().top+scrollY+2,behavior:'instant'})}")
  page.wait_for_function('(id)=>document.querySelector("canvas")?.dataset.scene===id',arg=scene['id'],timeout=25000)
  page.wait_for_timeout(750)
  page.screenshot(path=str(out/f'{i:02d}-{scene["id"]}.png'))
  rows.append({'scene':scene['id'],'status':page.locator('.renaissance-cinema').get_attribute('data-status')})
  print(json.dumps(rows[-1]),flush=True)
 browser.close()
(out/'manifest.json').write_text(json.dumps({'scenes':rows,'errors':errors,'note':'Manual dismissal of automatic login, then programmatic jump. Not a recreation of source trackpad input.'},indent=2))
assert not errors,errors
assert all(x['status']=='ready' for x in rows),rows
print('PASS: 13 current chapter captures, after dismissing login; no page errors')
