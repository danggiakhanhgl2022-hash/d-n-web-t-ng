"""Capture and verify the Online paper edge at explicit viewport positions."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/online-paper'
out.mkdir(parents=True,exist_ok=True)
samples=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
    page.wait_for_selector('input[name=username]',state='visible',timeout=60000)
    page.locator('.cinema-dialog-close').click()
    paper=page.locator('.cinema-chapter').nth(3).locator('.cinema-paper')
    for ratio in (.9,.65,.35):
        paper.evaluate('''(e,r)=>{document.documentElement.style.scrollBehavior='auto';
          scrollTo({top:scrollY+e.getBoundingClientRect().top-innerHeight*r,behavior:'instant'})}''',ratio)
        page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='online'",timeout=45000)
        page.wait_for_timeout(1100)
        state=paper.evaluate('''e=>{const s=getComputedStyle(e,'::before');return {
          top:e.getBoundingClientRect().top,filter:s.filter,height:s.height,content:s.content,
          turbulence:document.querySelector('#cinema-paper-edge feTurbulence')?.getAttribute('baseFrequency')};}''')
        assert abs(state['top']-800*ratio)<3,state
        assert 'cinema-paper-edge' in state['filter'] and state['content']!='none',state
        page.screenshot(path=str(out/f'paper-{int(ratio*100)}.png'))
        samples.append({'ratio':ratio,**state})
    page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(200)
    reduced=paper.evaluate("e=>({filter:getComputedStyle(e,'::before').filter,height:getComputedStyle(e,'::before').height})")
    assert reduced['filter']=='none',reduced
    assert not errors,errors
    browser.close()
(out/'checks.json').write_text(json.dumps({'samples':samples,'reduced':reduced,'errors':errors},indent=2),encoding='utf-8')
print('PASS: paper moves through three viewport positions; torn edge applied; reduced motion disables filter')
