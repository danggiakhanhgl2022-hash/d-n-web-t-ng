"""Exercise the redesigned opening and login with a mocked authentication API."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

out=Path(__file__).resolve().parents[1]/'runtime/verification/redesigned-entry';out.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 for width in (1440,970,390):
  page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  def api(route):
   path=route.request.url.split('/api/v1')[-1]
   if path=='/auth/me':route.fulfill(status=401,json={'error':'unauthenticated'});return
   if path=='/auth/login':route.fulfill(status=200,json={'user':{'id':'qa','username':'qa','display_name':'QA','role':'ADMIN','tenant_id':'qa'},'csrf_token':'qa'});return
   route.fulfill(status=200,json={'items':[],'questions':[],'sections':[]})
  page.route('**/api/v1/**',api)
  page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
  expect(page.locator('.cinema-cover')).to_be_visible(timeout=12000)
  page.wait_for_function("['ready','fallback'].includes(document.querySelector('.renaissance-cinema').dataset.status)",timeout=25000)
  expect(page.locator('input[name=username]')).to_be_visible(timeout=8000)
  dialog=page.locator('.cinema-login-dialog').bounding_box()
  assert dialog and abs(dialog['x']+dialog['width']/2-width/2)<2 and abs(dialog['y']+dialog['height']/2-450)<2,dialog
  assert dialog['height']<=860,dialog
  page.locator('.cinema-dialog-close').click()
  expect(page.locator('input[name=username]')).not_to_be_visible()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(out/f'cover-{width}.png'))
  page.locator('.cinema-enter').click()
  expect(page.locator('input[name=username]')).to_be_visible()
  page.screenshot(path=str(out/f'login-{width}.png'))
  page.keyboard.press('Escape');expect(page.locator('input[name=username]')).not_to_be_visible()
  page.locator('.cinema-enter').click()
  page.locator('input[name=username]').fill('qa');page.locator('input[name=password]').fill('test-password')
  page.locator('.cinema-login-dialog form button[type=submit], .cinema-login-dialog form button:not([type])').click()
  expect(page.locator('.app-shell')).to_be_visible(timeout=15000)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(out/f'workspace-{width}.png'))
  assert not errors,errors
  results.append({'width':width,'ok':True});page.close()
 browser.close()
(out/'checks.json').write_text(json.dumps(results,indent=2))
print('PASS: cover, dialog open/escape, mocked login, workspace and no horizontal overflow at 1440/970/390')
