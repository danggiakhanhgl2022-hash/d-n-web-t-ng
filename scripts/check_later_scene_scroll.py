import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('runtime/verification/later-scroll');out.mkdir(parents=True,exist_ok=True)
rows=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 page=b.new_page(viewport={'width':1366,'height':768});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3100',wait_until='networkidle')
 page.wait_for_timeout(500)
 for index,name in [(5,'marketing'),(6,'checkout'),(7,'operations')]:
  samples=[]
  for fraction in [.03,.12,.23]:
   page.evaluate("document.querySelector('dialog[open]')?.close()")
   page.locator('.cinema-chapter').nth(index).evaluate('''(el,f)=>scrollTo({top:el.getBoundingClientRect().top+scrollY+el.querySelector('.cinema-scene-space').offsetHeight*f,behavior:'instant'})''',fraction)
   page.wait_for_function("id=>document.querySelector('.cinema-webgl canvas')?.dataset.scene===id",arg=name,timeout=40000)
   page.wait_for_timeout(1600)
   sample=page.locator('.cinema-webgl canvas').evaluate("el=>({timeline:el.dataset.timeline,clips:JSON.parse(el.dataset.motionClips||'{}')})")
   samples.append(sample)
   page.screenshot(path=str(out/f'{name}-{fraction}.png'))
  assert len({s['timeline'] for s in samples})==3,(name,samples)
  if name in ('checkout','operations'):
   keys=samples[0]['clips'].keys()
   assert any(max(s['clips'][key] for s in samples)-min(s['clips'][key] for s in samples)>.05 for key in keys),(name,samples)
  rows.append({'scene':name,'samples':samples})
 assert not errors,errors
 (out/'results.json').write_text(json.dumps({'scenes':rows,'errors':errors},indent=2),encoding='utf8')
 print(json.dumps({'scenes':rows,'errors':errors}))
 b.close()
