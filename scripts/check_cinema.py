import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path('runtime/browser-qa/cinema');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--ignore-gpu-blocklist'])
    page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='no-preference')
    errors=[];warnings=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:warnings.append(m.text) if m.type in ('warning','error') else None)
    page.goto('http://127.0.0.1:3100',wait_until='networkidle')
    page.wait_for_timeout(6000)
    report=[]
    chapters=page.locator('.cinema-chapter')
    configs=json.loads(Path('frontend/public/renaissance/3d/scenes.json').read_text())
    indices=[0,1,4,12] if '--quick' in sys.argv else list(range(chapters.count()))
    for index in indices:
        box=chapters.nth(index).bounding_box()
        for phase in (.15,.55):
            y=box['y']+page.evaluate('scrollY')+(box['height']-1000)*phase
            page.evaluate('y=>scrollTo(0,y)',y)
            page.wait_for_function("id=>document.querySelector('.renaissance-cinema')?.dataset.status==='ready'&&document.querySelector('.cinema-webgl canvas')?.dataset.scene===id",arg=configs[index]['id'],timeout=30000)
            page.wait_for_timeout(1000 if phase==.15 else 350)
            canvas=page.locator('.cinema-webgl canvas')
            report.append({'index':index,'phase':phase,'status':page.locator('.renaissance-cinema').get_attribute('data-status'),'scene':canvas.get_attribute('data-scene') if canvas.count() else None,'timeline':canvas.get_attribute('data-timeline') if canvas.count() else None})
            if phase==.15:page.screenshot(path=str(out/f'scene-{index:02d}.png'))
            box=chapters.nth(index).bounding_box()
    page.locator('.cinema-enter').click()
    page.wait_for_timeout(500)
    assert page.locator('#login-form input[name=username]').is_visible()
    page.set_viewport_size({'width':390,'height':844})
    page.evaluate('scrollTo(0,0)');page.wait_for_timeout(1500)
    page.screenshot(path=str(out/'mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Mobile overflow'
    assert not errors,errors
    for index in indices:
        pair=[r for r in report if r['index']==index]
        assert len(pair)==2 and pair[0]['timeline']!=pair[1]['timeline'],pair
    assert not [w for w in warnings if 'THREE.' in w or 'Reference scene unavailable' in w],warnings
    page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(200)
    assert page.locator('.renaissance-cinema').get_attribute('data-reduced')=='true'
    print(json.dumps({'scenes':report,'errors':errors,'warnings':warnings}))
    (out/('quick-result.json' if '--quick' in sys.argv else 'result.json')).write_text(json.dumps({'scenes':report,'errors':errors,'warnings':warnings},indent=2),encoding='utf8')
    browser.close()
