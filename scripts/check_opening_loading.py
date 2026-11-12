"""Verify actual startup and recovery from hung auth, manifest, model and no WebGL."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

out=Path(__file__).resolve().parents[1]/'runtime/verification/opening-loading'
out.mkdir(parents=True,exist_ok=True)
rows=[]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 for case in ['normal','auth-hang','manifest-hang','model-hang','no-webgl']:
  context=browser.new_context(viewport={'width':1280,'height':800});page=context.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  if case=='auth-hang':page.route('**/api/v1/auth/me',lambda route:None)
  if case=='manifest-hang':page.route('**/renaissance/3d/scenes.json',lambda route:None)
  if case=='model-hang':page.route('**/EW26_Hero_251207v3_compressed-optimized.glb',lambda route:None)
  if case=='no-webgl':
   page.add_init_script("const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/i.test(type)?null:original.call(this,type,...args)}")
  page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
  expect(page.locator('.renaissance-cinema')).to_be_visible(timeout=5000)
  if case in ['normal','auth-hang']:
   page.wait_for_selector('canvas[data-scene=hero]',timeout=10000)
   start=page.locator('canvas').get_attribute('data-timeline')
   page.wait_for_timeout(900)
   end=page.locator('canvas').get_attribute('data-timeline')
   assert float(end)>float(start),(case,start,end)
   if case=='auth-hang':page.wait_for_timeout(5000)
   else:page.wait_for_timeout(2700)
   assert page.locator('.renaissance-cinema').get_attribute('data-status')=='ready'
  else:
   page.wait_for_timeout(1000)
   if case!='no-webgl':
    assert page.locator('.cinema-fallback').evaluate("e=>+getComputedStyle(e).opacity")>0
    page.screenshot(path=str(out/f'{case}-while-loading.png'))
   page.wait_for_function("document.querySelector('.renaissance-cinema').dataset.status==='fallback'",timeout=24000)
   assert page.locator('canvas').count()==0
  expect(page.locator('.cinema-cover')).to_be_visible(timeout=8000)
  expect(page.locator('input[name=username]')).to_be_visible(timeout=8000)
  expect(page.locator('input[name=password]')).to_be_visible()
  page.screenshot(path=str(out/f'{case}-settled.png'))
  assert not errors,(case,errors)
  row={'case':case,'status':page.locator('.renaissance-cinema').get_attribute('data-status'),'login_visible':True,'errors':errors};rows.append(row);print(json.dumps(row),flush=True)
  page.unroute_all(behavior='ignoreErrors')
  context.close()
 browser.close()
(out/'checks.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('PASS: opening runs without waiting for auth; no indefinite dark/loading state under simulated failures')
