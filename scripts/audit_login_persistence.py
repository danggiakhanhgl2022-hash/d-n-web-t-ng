"""Capture the automatic login after the intro and check it stays visible."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(__file__).resolve().parents[1]/'runtime/verification/login-persistence';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 page=b.new_page(viewport={'width':1280,'height':800});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
 page.wait_for_selector('input[name=username]',state='visible',timeout=30000)
 snapshots=[]
 for i in range(4):
  page.wait_for_timeout(2000)
  snapshots.append(page.locator('input[name=username]').evaluate("e=>({visible:!!e.getClientRects().length,opacity:getComputedStyle(e).opacity,parentOpacity:getComputedStyle(e.closest('.login-panel')).opacity,dialogOpen:e.closest('dialog').open})"))
  page.screenshot(path=str(out/f'{i}.png'))
 (out/'checks.json').write_text(json.dumps({'snapshots':snapshots,'errors':errors},indent=2))
 b.close()
print(json.dumps({'snapshots':snapshots,'errors':errors}))
