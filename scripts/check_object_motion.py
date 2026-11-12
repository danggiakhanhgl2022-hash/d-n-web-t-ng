"""Check named rig clocks across real scroll positions and while idle."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/object-motion';out.mkdir(parents=True,exist_ok=True)
results={};errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 page=browser.new_page(viewport={'width':1280,'height':800});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
 page.wait_for_selector('input[name=username]',state='visible',timeout=30000)
 page.locator('.cinema-dialog-close').click()
 for index,scene in [(1,'sidekick'),(2,'agentic'),(3,'online'),(4,'retail')]:
  samples=[]
  for fraction in (0.02,.25,.5,.8):
   page.locator('.cinema-chapter').nth(index).evaluate('''(e,f)=>{
    document.documentElement.style.scrollBehavior='auto';
    scrollTo({top:e.getBoundingClientRect().top+scrollY+e.querySelector('.cinema-scene-space').offsetHeight*f,behavior:'instant'})
   }''',fraction)
   page.wait_for_function('(id)=>document.querySelector("canvas")?.dataset.scene===id',arg=scene,timeout=30000)
   page.wait_for_timeout(1100)
   canvas=page.locator('canvas').first
   values=json.loads(canvas.get_attribute('data-motion-clips') or '{}')
   samples.append({'fraction':fraction,'timeline':float(canvas.get_attribute('data-timeline')),'clips':values})
   page.screenshot(path=str(out/f'{scene}-{int(fraction*100):02}.png'))
  results[scene]=samples
  print(scene,json.dumps(samples),flush=True)
 # Authored Sidekick ring tracks, Agentic book and Retail hub must advance
 # over the scroll, not just report that a canvas exists.
 for scene,part in [('sidekick','RingAction'),('agentic','3:Scene'),('retail','2:Scene')]:
  keys=[k for k in results[scene][0]['clips'] if part in k]
  assert keys,(scene,results[scene])
  assert any(max(s['clips'][k] for s in results[scene])-min(s['clips'][k] for s in results[scene])>.05 for k in keys),(scene,results[scene])
 # Loop clips without explicit progress should keep moving when scroll stops.
 canvas=page.locator('canvas').first
 page.locator('.cinema-chapter').nth(3).evaluate("e=>scrollTo({top:e.getBoundingClientRect().top+scrollY+20,behavior:'instant'})")
 page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='online'",timeout=30000)
 page.wait_for_timeout(1200);first=json.loads(canvas.get_attribute('data-motion-clips'))
 page.wait_for_timeout(800);second=json.loads(canvas.get_attribute('data-motion-clips'))
 for part in ('handarmature','brushAction'):
  key=next((k for k in first if part in k),None)
  assert key and key in second and abs(first[key]-second[key])>.05,(part,first,second)
 assert not errors,errors
 results['online_idle']={'first':first,'second':second}
 (out/'checks.json').write_text(json.dumps({'results':results,'errors':errors},indent=2),encoding='utf-8')
 browser.close()
print('PASS: ring, book and hub advance with scroll; hand and brush loops change while idle; no page errors')
