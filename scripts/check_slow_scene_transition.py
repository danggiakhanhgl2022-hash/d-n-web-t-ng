"""A late scene load must retain the old canvas and show the transition."""
import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
out=root/'runtime/verification/slow-scene-transition';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 page=browser.new_page(viewport={'width':1280,'height':800});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def delay(route):
  time.sleep(1.8)
  route.continue_()
 page.route('**/DeveloperScene.theatre-project-state_5.json',delay)
 page.add_init_script('''window.changeSamples=[];function sample(){
  const root=document.querySelector('.renaissance-cinema'),c=document.querySelector('.cinema-webgl canvas');
  if(root?.dataset.chapter==='12'&&c)changeSamples.push({scene:c.dataset.scene,status:root.dataset.status,opacity:getComputedStyle(c.parentElement).opacity,progress:+c.dataset.transitionProgress});
  requestAnimationFrame(sample)
 }requestAnimationFrame(sample)''')
 page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
 page.wait_for_selector('input[name=username]',state='visible',timeout=30000)
 page.locator('.cinema-dialog-close').click()
 page.locator('.cinema-chapter').nth(12).evaluate("e=>{document.documentElement.style.scrollBehavior='auto';scrollTo({top:e.getBoundingClientRect().top+scrollY+2,behavior:'instant'})}")
 page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='developer'",timeout=30000)
 page.wait_for_timeout(1400)
 samples=page.evaluate('changeSamples')
 waiting=[x for x in samples if x['scene']=='hero']
 arrived=[x for x in samples if x['scene']=='developer']
 assert waiting and all(x['status']=='ready' and float(x['opacity'])>.95 for x in waiting),waiting[:10]
 assert arrived and min(x['progress'] for x in arrived)<.5 and any(.3<x['progress']<.9 for x in arrived) and arrived[-1]['progress']==1,arrived
 assert not errors,errors
 page.screenshot(path=str(out/'developer.png'))
 (out/'checks.json').write_text(json.dumps({'samples':samples,'errors':errors},indent=2))
 browser.close()
print('PASS: slow scene load keeps previous canvas visible and plays intermediate transition')
