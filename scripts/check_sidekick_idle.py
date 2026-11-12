"""Check slow armillary animation at rest and reduced-motion behavior."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/sidekick-idle'
out.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
    page.wait_for_selector('input[name=username]',state='visible',timeout=60000)
    page.locator('.cinema-dialog-close').click()
    page.locator('.cinema-chapter').nth(1).evaluate('''e=>{
      document.documentElement.style.scrollBehavior='auto';
      scrollTo({top:e.getBoundingClientRect().top+scrollY+e.querySelector('.cinema-scene-space').offsetHeight*.5,behavior:'instant'});
    }''')
    page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='sidekick'",timeout=45000)
    page.wait_for_timeout(2000)
    def rings():
        clips=json.loads(page.locator('canvas').first.get_attribute('data-motion-clips'))
        return {k:v for k,v in clips.items() if 'RingAction' in k}
    def poses():
        return json.loads(page.locator('canvas').first.get_attribute('data-ring-transforms'))
    first=rings();first_pose=poses();page.screenshot(path=str(out/'idle-first.png'))
    page.wait_for_timeout(1000);second=rings();second_pose=poses();page.screenshot(path=str(out/'idle-second.png'))
    assert len(first)==4 and any(abs(first[k]-second[k])>.005 for k in first),(first,second)
    assert len(first_pose)==4 and any(max(abs(a-b) for a,b in zip(first_pose[k],second_pose[k]))>.0001 for k in first_pose),(first_pose,second_pose)
    page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(500)
    reduced_first=rings();page.wait_for_timeout(1000);reduced_second=rings()
    assert all(abs(reduced_first[k]-reduced_second[k])<.0002 for k in reduced_first),(reduced_first,reduced_second)
    assert not errors,errors
    browser.close()
(out/'checks.json').write_text(json.dumps({'first':first,'second':second,'first_pose':first_pose,'second_pose':second_pose,'reduced_first':reduced_first,'reduced_second':reduced_second,'errors':errors},indent=2),encoding='utf-8')
print('PASS: four rings sampled; idle clip time changes; reduced motion holds still; no page errors')
