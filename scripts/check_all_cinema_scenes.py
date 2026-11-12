"""Walk all public chapters of the running web; read-only, no customer data."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
out=root/'runtime/verification/video-comparison'
out.mkdir(parents=True,exist_ok=True)
configs=json.loads((root/'frontend/public/renaissance/3d/scenes.json').read_text(encoding='utf-8'))
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''window.sceneTransitions={};function sample(){const c=document.querySelector('canvas[data-scene]');if(c){const id=c.dataset.scene;(sceneTransitions[id]??=[]).push(+c.dataset.transitionProgress)}requestAnimationFrame(sample)}requestAnimationFrame(sample)''')
    page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
    page.wait_for_selector('canvas[data-scene]',timeout=60000)
    page.wait_for_timeout(4500)
    if page.locator('.cinema-login-dialog').is_visible():page.locator('.cinema-dialog-close').click()
    for i,config in enumerate(configs):
        page.locator('.cinema-chapter').nth(i).evaluate('''e=>{
          document.documentElement.style.scrollBehavior='auto';
          window.scrollTo({top:e.getBoundingClientRect().top+scrollY+2,behavior:'instant'});
        }''')
        try:
            page.wait_for_function('(id)=>document.querySelector("canvas")?.dataset.scene===id',arg=config['id'],timeout=15000)
            page.wait_for_timeout(1000)
            status=page.locator('.renaissance-cinema').get_attribute('data-status')
            timeline=page.locator('canvas').get_attribute('data-timeline')
            page.screenshot(path=str(out/f"scene-{i:02d}-{config['id']}.png"))
            page.wait_for_timeout(750)
            later=page.locator('canvas').get_attribute('data-timeline')
            page.screenshot(path=str(out/f"scene-{i:02d}-{config['id']}-later.png"))
            rows.append({'scene':config['id'],'status':status,'timeline':timeline,'later':later})
        except Exception as error:
            rows.append({'scene':config['id'],'status':'FAIL','error':str(error)[:250]})
        print(json.dumps(rows[-1]),flush=True)
    transitions=page.evaluate('sceneTransitions')
    browser.close()
(out/'all-scenes.json').write_text(json.dumps({'scenes':rows,'errors':errors,'transition_samples':transitions},indent=2),encoding='utf-8')
assert not errors,errors
assert all(r['status']=='ready' for r in rows),rows
for config in configs[1:]:
    values=transitions.get(config['id'],[])
    assert any(.15<v<.9 for v in values),(config['id'],values[:20])
print(f'PASS: all {len(rows)} scenes rendered, with intermediate transitions, without page errors')
