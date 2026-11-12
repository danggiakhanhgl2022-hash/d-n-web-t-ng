from pathlib import Path
import json,re
from playwright.sync_api import sync_playwright

out=Path('runtime/reference-video');out.mkdir(exist_ok=True,parents=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    requests=[]
    page.on('response',lambda r:requests.append({'url':r.url,'status':r.status,'type':r.request.resource_type}))
    page.goto('https://www.shopify.com/editions/winter2026',wait_until='domcontentloaded',timeout=90000)
    page.wait_for_timeout(12000)
    page.screenshot(path=str(out/'original-opening.png'))
    print(json.dumps(page.evaluate('''()=>({canvas:document.querySelectorAll('canvas').length,videos:[...document.querySelectorAll('video')].map(v=>({src:v.currentSrc,poster:v.poster,loop:v.loop})),scripts:[...document.scripts].map(s=>s.src).filter(Boolean),height:document.documentElement.scrollHeight})''')))
    for y in (1000,2500,5000,10000):
        page.evaluate('y=>window.scrollTo(0,y)',y);page.wait_for_timeout(1500)
    (out/'network.json').write_text(json.dumps(requests,indent=2),encoding='utf8')
    print(json.dumps([r for r in requests if any(ext in r['url'] for ext in ('.glb','.gltf','.ktx','.bin','.webm','.mp4'))]))
    browser.close()
