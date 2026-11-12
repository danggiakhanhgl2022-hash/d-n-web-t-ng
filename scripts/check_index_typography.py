"""Verify the reported small/white chapter index, including mixed light/dark rows."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

out=Path(__file__).resolve().parents[1]/'runtime/verification/typography-repair';out.mkdir(parents=True,exist_ok=True)
rows=[]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 for width in (1440,970,768,390):
  page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
  page.wait_for_selector('input[name=username]',timeout=10000)
  page.wait_for_timeout(1000)
  expect(page.locator('input[name=username]')).to_be_visible()
  assert page.locator('.login-box .field>span').first.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')>=16
  if width>760:
   assert page.locator('.cinema-index button').first.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')>=15
   menu=page.locator('.cinema-index').bounding_box();form=page.locator('#login-form').bounding_box()
   assert menu and form and menu['x']+menu['width']<form['x'],(menu,form)
   assert menu['height']<=380 and abs(menu['y']+menu['height']-(900-28))<2,menu
   page.screenshot(path=str(out/f'opening-layout-{width}.png'))
   page.locator('.cinema-paper').first.evaluate("e=>{document.documentElement.style.scrollBehavior='auto';const m=document.querySelector('.cinema-index').getBoundingClientRect();scrollTo({top:e.getBoundingClientRect().top+scrollY-(m.top+m.height*.5),behavior:'instant'})}")
   page.wait_for_timeout(1000)
   data=page.locator('.cinema-index button').evaluate_all("es=>es.map(e=>({surface:e.dataset.surface,color:getComputedStyle(e).color,numberRight:e.querySelector('small').getBoundingClientRect().right}))")
   assert any(x['surface']=='light' for x in data) and any(x['surface']=='dark' for x in data),data
   for x in data:
    rgb=[int(v) for v in x['color'].replace('rgb(','').replace(')','').split(',')]
    assert (max(rgb)<100 if x['surface']=='light' else min(rgb)>200),x
   assert max(x['numberRight'] for x in data)-min(x['numberRight'] for x in data)<1,data
   assert page.locator('.cinema-header').get_attribute('data-surface')=='dark'
   assert page.locator('.cinema-header').evaluate('e=>getComputedStyle(e).color')=='rgb(255, 249, 234)'
   page.screenshot(path=str(out/f'mixed-background-{width}.png'))
   page.locator('.cinema-chapter').nth(12).evaluate("e=>scrollTo({top:e.getBoundingClientRect().top+scrollY+100,behavior:'instant'})")
   page.wait_for_timeout(1000)
   expect(page.locator('.cinema-index button').last).to_have_attribute('data-surface','light')
   page.screenshot(path=str(out/f'light-background-{width}.png'))
  else:
   expect(page.locator('.cinema-index')).not_to_be_visible()
   page.screenshot(path=str(out/'mobile-login.png'))
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  rows.append({'width':width,'passed':True,'errors':errors});page.close()
 browser.close()
(out/'checks.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('PASS: readable form/index sizes, aligned numbers, contrast per row on mixed backgrounds, no menu/form overlap or horizontal overflow')
