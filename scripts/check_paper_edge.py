"""Check animated paper edge without moving the reading surface or breaking reduced motion."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/effects-refinement';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True);page=b.new_page(viewport={'width':1280,'height':800});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded');page.wait_for_selector('canvas[data-scene]',timeout=10000);page.wait_for_timeout(3400)
 paper=page.locator('.cinema-paper').first
 paper.evaluate("e=>{document.documentElement.style.scrollBehavior='auto';scrollTo({top:e.getBoundingClientRect().top+scrollY-innerHeight*.5,behavior:'instant'})}")
 page.wait_for_timeout(1200)
 a=page.locator('#cinema-paper-edge feTurbulence').get_attribute('baseFrequency');box=paper.bounding_box()
 assert 'url(' in paper.evaluate("e=>getComputedStyle(e,'::before').filter")
 page.screenshot(path=str(out/'paper-edge-a.png'),clip={'x':0,'y':box['y']-50,'width':1280,'height':100})
 page.wait_for_timeout(800)
 c=page.locator('#cinema-paper-edge feTurbulence').get_attribute('baseFrequency');after=paper.bounding_box()
 page.screenshot(path=str(out/'paper-edge-b.png'),clip={'x':0,'y':after['y']-50,'width':1280,'height':100})
 assert a!=c,(a,c)
 assert abs(box['y']-after['y'])<1,(box,after)
 page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(100)
 assert paper.evaluate("e=>getComputedStyle(e,'::before').filter")=='none'
 assert not errors,errors
 b.close()
(out/'paper-edge-checks.json').write_text(json.dumps({'before':a,'after':c,'layout_stable':True,'reduced_motion_static':True,'errors':errors},indent=2),encoding='utf-8')
print('PASS: paper texture moves, reading layout stays fixed, reduced motion disables deformation')
