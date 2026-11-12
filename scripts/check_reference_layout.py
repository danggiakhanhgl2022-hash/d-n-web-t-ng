"""Check the reconstructed scene/paper flow, mobile and 0.1s review viewer."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

root=Path(__file__).resolve().parents[1]
out=root/'runtime/verification/video-comparison'
out.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for width,height,reduced in ((1440,900,False),(390,844,False),(390,844,True)):
        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce' if reduced else 'no-preference')
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
        page.wait_for_selector('canvas[data-scene]',timeout=60000)
        page.wait_for_timeout(3400)
        box=page.locator('#login-form').bounding_box()
        assert box and box['x']>=0 and box['y']>=0 and box['y']+box['height']<=height,box
        assert page.locator('.cinema-feature').count()==36
        assert page.locator('.cinema-chapter').count()==13
        page.locator('.cinema-paper').first.evaluate("e=>{document.documentElement.style.scrollBehavior='auto';scrollTo({top:e.getBoundingClientRect().top+scrollY,behavior:'instant'})}")
        page.wait_for_function("document.querySelector('.renaissance-cinema').dataset.paper==='true'")
        page.wait_for_timeout(800)
        page.wait_for_function("(()=>{const i=document.querySelector('.cinema-paper-showcase img');return i?.complete&&i.naturalWidth>0})()",timeout=15000)
        sizes=page.evaluate('''()=>{
          const a=[...document.querySelectorAll('.cinema-chapter')];
          return {viewport:innerWidth,document:document.documentElement.scrollWidth,papers:a.slice(1).map((c,i)=>{const p=c.querySelector('.cinema-paper'),next=a[i+2];return {position:getComputedStyle(p).position,overlap:next?p.getBoundingClientRect().bottom>next.getBoundingClientRect().top+1:false}})};
        }''')
        assert sizes['document']<=width,sizes
        assert all(r['position']=='relative' and not r['overlap'] for r in sizes['papers']),sizes
        assert not errors,errors
        page.screenshot(path=str(out/f'paper-flow-{width}-reduced-{reduced}.png'))
        results.append(dict(sizes,reduced=reduced,errors=errors))
        page.close()
    page=browser.new_page()
    page.goto((root/'runtime/reference-video/tenths/index.html').as_uri())
    page.locator('#scrub').fill('17');page.locator('#scrub').dispatch_event('input')
    expect(page.locator('#time')).to_contain_text('1.7 s')
    page.locator('#next').click();expect(page.locator('#time')).to_contain_text('1.8 s')
    page.locator('#prev').click();expect(page.locator('#time')).to_contain_text('1.7 s')
    page.locator('#full').check()
    expect(page.locator('#frame')).to_have_attribute('src','t-01.7-full.jpg')
    page.close();browser.close()
(out/'reference-layout-checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('PASS: 13 chapters, 36 information cards, paper flow/no overlap, mobile/reduced motion, 0.1s viewer controls')
