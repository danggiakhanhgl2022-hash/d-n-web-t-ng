"""Verify the published comparison viewer and its actual image pairs."""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
out=Path(__file__).resolve().parents[1]/'runtime/verification/motion-review';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:3100/motion-review/index.html')
    page.wait_for_function("document.querySelector('#source').naturalWidth>0")
    for mark in (60,180,640,1080,2670,3440):
        page.locator('#slider').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input"))}',mark)
        page.wait_for_function("document.querySelector('#source').complete&&document.querySelector('#web').complete&&document.querySelector('#web').naturalWidth>0")
        expect(page.locator('#web')).to_be_visible()
        page.screenshot(path=str(out/f'compare-{mark:04d}.png'))
    page.locator('#slider').evaluate('(e)=>{e.value=3467;e.dispatchEvent(new Event("input"))}')
    expect(page.locator('#web')).not_to_be_visible()
    page.locator('#slider').evaluate('(e)=>{e.value=60;e.dispatchEvent(new Event("input"))}')
    page.locator('#next').click();expect(page.locator('#time')).to_have_text('0.61 giây')
    page.locator('#prev').click();expect(page.locator('#time')).to_have_text('0.60 giây')
    page.locator('#play').click();page.wait_for_timeout(150);page.locator('#play').click()
    assert float(page.locator('#slider').input_value())>60
    assert not errors,errors
    browser.close()
print('PASS: paired source/web images, 0.01s steps, play, later scenes and outro boundary; no page errors')
