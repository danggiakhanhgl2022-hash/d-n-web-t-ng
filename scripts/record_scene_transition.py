"""Record an actual transition, preserving capture times for source comparison."""
import argparse
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

args=argparse.ArgumentParser();args.add_argument('--round',default='round-1');args.add_argument('--duration',type=float,default=.85);options=args.parse_args()
root=Path(__file__).resolve().parents[1];out=root/'runtime/verification/effects-refinement'/options.round;out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 context=browser.new_context(viewport={'width':1440,'height':900},record_video_dir=str(out),record_video_size={'width':1440,'height':900})
 page=context.new_page();errors=[];stream=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:errors.append(m.text) if m.type=='error' and any(s in m.text for s in ('Shader','WebGL','GL_INVALID')) else None)
 page.add_init_script('''window.transitionFrames=[];function record(t){const c=document.querySelector('canvas[data-transition-progress]');if(c?.dataset.scene==='sidekick')window.transitionFrames.push({wall:t,progress:+c.dataset.transitionProgress});requestAnimationFrame(record)}requestAnimationFrame(record);''')
 page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
 page.wait_for_selector('canvas[data-scene=hero]',timeout=60000);page.wait_for_timeout(3600)
 if page.locator('.cinema-login-dialog').is_visible():page.locator('.cinema-dialog-close').click()
 assert page.locator('canvas').get_attribute('data-reveal-surface')=='reference'
 cdp=context.new_cdp_session(page)
 def frame(event):
  stream.append((event['metadata']['timestamp'],event['data']));cdp.send('Page.screencastFrameAck',{'sessionId':event['sessionId']})
 cdp.on('Page.screencastFrame',frame);cdp.send('Page.startScreencast',{'format':'jpeg','quality':90,'maxWidth':960,'maxHeight':600,'everyNthFrame':1})
 page.locator('.cinema-chapter').nth(1).evaluate("e=>{document.documentElement.style.scrollBehavior='auto';scrollTo({top:e.getBoundingClientRect().top+scrollY+e.querySelector('.cinema-scene-space').offsetHeight*.15,behavior:'instant'})}")
 page.wait_for_function("document.querySelector('canvas')?.dataset.scene==='sidekick'",timeout=30000)
 page.wait_for_timeout(1500)
 frames=page.evaluate('window.transitionFrames');origin=page.evaluate('performance.timeOrigin')/1000+frames[0]['wall']/1000-frames[0]['progress']*options.duration
 cdp.send('Page.stopScreencast');captures=[]
 for i in range(12):
  target=i/10;stamp,data=min(stream,key=lambda s:abs(s[0]-origin-target));name=f'transition-{target:.1f}.jpg';(out/name).write_bytes(base64.b64decode(data));captures.append({'target':target,'actual':round(stamp-origin,3),'image':name})
 video=page.video;context.close();video.save_as(str(out/'hero-to-sidekick.webm'));browser.close()
(out/'checks.json').write_text(json.dumps({'captures':captures,'frames':frames,'errors':errors,'reference_mud':True,'transition_duration':options.duration},indent=2),encoding='utf-8')
assert not errors,errors
assert any(.2<f['progress']<.8 for f in frames),frames
assert frames[-1]['progress']==1,frames[-1]
print(f'PASS {options.round}: reference texture loaded; transition traversed intermediate frames; no page/shader errors')
