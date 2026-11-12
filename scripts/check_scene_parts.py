"""Compare every split GLB clip with its original on cloned scene graphs."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'runtime/verification/scene-parts'
out.mkdir(parents=True,exist_ok=True)
errors=[];results={}
scene_ids=[item['id'] for item in json.loads((out.parents[2]/'frontend/public/renaissance/3d/scenes.json').read_text(encoding='utf-8'))]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:3100/?motionAudit=1',wait_until='domcontentloaded')
    page.wait_for_selector('input[name=username]',state='visible',timeout=60000)
    page.locator('.cinema-dialog-close').click()
    chapters=page.locator('.cinema-chapter')
    for index in range(chapters.count()):
        chapter=chapters.nth(index)
        chapter.evaluate("e=>scrollTo({top:e.getBoundingClientRect().top+scrollY+20,behavior:'instant'})")
        page.wait_for_function('(n)=>+document.querySelector(".renaissance-cinema").dataset.chapter===n',arg=index,timeout=30000)
        page.wait_for_function('(id)=>document.querySelector("canvas[data-scene-parts]")?.dataset.scene===id',arg=scene_ids[index],timeout=60000)
        canvas=page.locator('canvas[data-scene-parts]')
        scene=canvas.get_attribute('data-scene')
        reports=json.loads(canvas.get_attribute('data-scene-parts'))
        results[scene]=reports
        for report in reports:
            assert not report['unresolved'],(scene,report)
            assert sum(report['parts'].values())==report['sourceTracks'],(scene,report)
            assert report['audit']['maximumTransformDifference']<1e-6,(scene,report)
        print(scene,len(reports),'clips',flush=True)
    assert len(results)==chapters.count(),list(results)
    assert not errors,errors
    browser.close()
(out/'checks.json').write_text(json.dumps({'scenes':results,'errors':errors},indent=2),encoding='utf-8')
print('PASS: all scene clips retain tracks and reassemble at seven sampled poses')
