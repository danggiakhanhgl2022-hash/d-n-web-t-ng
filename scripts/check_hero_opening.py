"""Verify automatic turning reveal, rig extension/retraction, and delayed UI."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(__file__).resolve().parents[1] / "runtime/verification/hero-opening"
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script('''window.rigSamples=[];function sampleRig(){
      const c=document.querySelector('canvas[data-hero-progress]');
      if(c)window.rigSamples.push({time:+c.dataset.timeline,rig:+c.dataset.heroProgress});
      requestAnimationFrame(sampleRig);
    }requestAnimationFrame(sampleRig);''')
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Shader" in m.text else None)
    page.goto("http://127.0.0.1:3100", wait_until="domcontentloaded")
    page.wait_for_selector("canvas[data-hero-progress]", timeout=60000)
    assert not page.locator('input[name=username]').is_visible()
    samples = []
    for i in range(15):
        samples.append(page.evaluate('''() => {
          const c=document.querySelector('canvas[data-hero-progress]'),card=document.querySelector('.cinema-cover');
          return {time:+c.dataset.timeline,rig:+c.dataset.heroProgress,turn:+c.dataset.heroTurn,form:+getComputedStyle(card).opacity,visible:getComputedStyle(card).visibility,scroll:scrollY};
        }'''))
        if i in (1, 3, 6, 10, 14):
            page.screenshot(path=str(out / f"phase-{i:02d}.png"))
        page.wait_for_timeout(250)
    # Source camera roll starts at .27 radians; no longer spin the flat image 1.8rad.
    assert samples[0]["turn"] > .05, samples
    assert samples[0]["visible"] == "visible", samples
    # Screenshots can stall the Python loop under GPU load. Check the rendered
    # frame stream so a short extended pose is not missed between captures.
    rendered = page.evaluate('window.rigSamples')
    extended = [s for s in rendered if s["time"] > .8 and s["rig"] > .99]
    assert extended, rendered
    assert samples[-1]["rig"] < .12 and samples[-1]["form"] == 1, samples
    assert abs(samples[-1]["turn"]) < .00001 and all(s["scroll"] == 0 for s in samples), samples
    assert not errors, errors
    idle = []
    for _ in range(6):
        idle.append(float(page.locator("canvas[data-rig-pose]").get_attribute("data-rig-pose")))
        page.wait_for_timeout(400)
    assert max(idle) - min(idle) > .005, idle
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(150)
    assert page.locator(".cinema-cover").is_visible()
    assert page.locator('input[name=username]').is_visible()
    page.locator('.cinema-dialog-close').click()
    page.wait_for_timeout(250)
    assert not page.locator('input[name=username]').is_visible()
    page.locator('.cinema-enter').click()
    assert page.locator('input[name=username]').is_visible()
    page.emulate_media(reduced_motion="no-preference")
    page.reload(wait_until='domcontentloaded')
    page.wait_for_selector('canvas[data-hero-progress]',timeout=60000)
    assert not page.locator('input[name=username]').is_visible()
    page.wait_for_selector('input[name=username]',state='visible',timeout=12000)
    browser.close()
(out / "checks.json").write_text(json.dumps({"samples": samples, "idle": idle, "errors": errors}, indent=2), encoding="utf-8")
print("PASS: no scroll; rotating reveal; rig extends/retracts and continues gentle idle; reduced motion and login accessible")
