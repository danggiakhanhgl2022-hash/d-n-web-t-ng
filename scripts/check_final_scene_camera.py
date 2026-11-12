import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('runtime/verification/final-camera');out.mkdir(parents=True,exist_ok=True)
rows=[];errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 page=b.new_page(viewport={'width':1100,'height':520});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3100',wait_until='networkidle')
 for f in [.05,.45,.7,.9]:
  page.evaluate("document.querySelector('dialog[open]')?.close()")
  page.locator('#cinema-12').evaluate('(e,f)=>scrollTo({top:scrollY+e.getBoundingClientRect().top+e.querySelector(".cinema-scene-space").offsetHeight*f,behavior:"instant"})',f)
  page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='developer'",timeout=40000)
  page.wait_for_timeout(1700)
  row=page.locator('canvas').evaluate('e=>({cameraTime:Number(e.dataset.cameraTimeline),position:e.dataset.cameraPosition,clips:e.dataset.motionClips})')
  row['fraction']=f;rows.append(row);page.screenshot(path=str(out/f'progress-{f}.png'))
 assert all(a['cameraTime']<b['cameraTime'] for a,b in zip(rows,rows[1:])),rows
 assert len({r['position'] for r in rows})==4,rows
 assert not errors,errors
 (out/'result.json').write_text(json.dumps({'samples':rows,'errors':errors},indent=2),encoding='utf8')
 print(json.dumps(rows));b.close()
