"""Measure visible scroll motion against the running local UI, without changing data."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width":1440,"height":1000}, reduced_motion="no-preference")
    errors=[]
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:3100",wait_until="networkidle")
    page.locator(".renaissance-journey").wait_for()
    assert page.locator(".scene.active").evaluate("el=>getComputedStyle(el).animationName") == "arrival-camera"
    track=page.locator(".renaissance-journey")
    box=track.bounding_box()
    samples=[]
    for progress in (0,.5,1):
        page.evaluate("y=>window.scrollTo(0,y)",box["y"]+(box["height"]-1000)*progress)
        page.wait_for_timeout(150)
        samples.append(page.locator(".renaissance-chapter").evaluate_all("els=>els.map(el=>({opacity:Number(getComputedStyle(el).opacity),transform:getComputedStyle(el).transform}))"))
    assert samples[0][0]["opacity"]>.95
    assert samples[1][1]["opacity"]>.95
    assert samples[2][2]["opacity"]>.95
    assert samples[0][0]["transform"] != samples[1][0]["transform"]
    output=Path("runtime/browser-qa");output.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(output/"motion-desktop.png"))
    page.set_viewport_size({"width":390,"height":844})
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(200)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "Mobile horizontal overflow"
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(200)
    assert page.locator(".renaissance-film-stage").evaluate("el=>getComputedStyle(el).position")=="relative"
    assert all(x==1 for x in page.locator(".renaissance-chapter").evaluate_all("els=>els.map(el=>Number(getComputedStyle(el).opacity))"))
    assert not errors, errors
    result={"scroll_samples":samples,"camera_animation":True,"mobile_no_overflow":True,"reduced_motion":True,"runtime_errors":errors}
    (output/"motion-result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
    browser.close()
