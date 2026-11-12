"""Record the running production opening and timestamped evidence, without writes to app data."""
import json
import base64
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--interval',type=float,default=.1);options=parser.parse_args()
assert options.interval in (.1,.05,.01)
out = root / ('frontend/public/motion-review/web' if options.interval==.01 else 'runtime/verification/opening-005' if options.interval==.05 else 'runtime/verification/video-comparison')
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    context = browser.new_context(viewport={"width":1440,"height":900}, record_video_dir=str(out), record_video_size={"width":1440,"height":900})
    page = context.new_page()
    stream=[]
    cdp=context.new_cdp_session(page)
    def frame(event):
        stream.append((event['metadata']['timestamp'],event['data']))
        cdp.send('Page.screencastFrameAck',{'sessionId':event['sessionId']})
    cdp.on('Page.screencastFrame',frame)
    cdp.send('Page.startScreencast',{'format':'jpeg','quality':88,'maxWidth':960,'maxHeight':600,'everyNthFrame':1})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script('''window.motionFrames=[];
      function capture(t){
        const c=document.querySelector('canvas[data-hero-progress]');
        if(c && (!window.motionFrames.length || t-window.motionFrames.at(-1).wall>45)){
          const cover=document.querySelector('.cinema-cover');
          window.motionFrames.push({wall:t,opening:+getComputedStyle(document.querySelector('.renaissance-cinema')).getPropertyValue('--opening')*3.2,time:+c.dataset.timeline,rig:+c.dataset.heroProgress,pose:+c.dataset.rigPose,turn:+c.dataset.heroTurn,cover:+getComputedStyle(cover).opacity,scroll:scrollY});
        }
        requestAnimationFrame(capture);
      }requestAnimationFrame(capture);''')
    page.goto('http://127.0.0.1:3100', wait_until='domcontentloaded')
    page.wait_for_selector('canvas[data-hero-progress]', timeout=60000)
    # Continuous CDP frames avoid the ~0.5s GPU stalls caused by taking a full
    # screenshot at every marker. Choose frames by their actual capture times.
    page.wait_for_timeout(7400)
    frames = page.evaluate('window.motionFrames')
    first=next(f for f in frames if 0<f['opening']<1)
    origin=page.evaluate('performance.timeOrigin')/1000+first['wall']/1000-first['opening']
    cdp.send('Page.stopScreencast')
    captures=[]
    targets=sorted(set([round(i*options.interval,2) for i in range(round(3.2/options.interval)+1)]+[.25,.75,4.25,5,7]))
    for target in targets:
        stamp,data=min(stream,key=lambda item:abs(item[0]-origin-target))
        path=f'web-{target:05.2f}.jpg'
        (out/path).write_bytes(base64.b64decode(data))
        captures.append({'target_s':target,'actual_s':round(stamp-origin,3),'image':path})
    video = page.video
    context.close()
    video.save_as(str(out / 'web-opening.webm'))
    browser.close()
usable = [f for f in frames if .8<f['time']<1.5]
peak=max((f['rig'] for f in usable),default=0)
checks={"no_js_errors":not errors,"no_scroll":all(f['scroll']==0 for f in frames),"rig_extension_peak":peak,"rig_retracted":frames[-1]['rig']<.12,"cover_visible_at_end":frames[-1]['cover']==1,"idle_pose_range":max(f['pose'] for f in frames[-20:])-min(f['pose'] for f in frames[-20:])}
(out/'recording.json').write_text(json.dumps({"captures":captures,"capture_method":"continuous CDP screencast; no repeated screenshot stalls","checks":checks,"errors":errors,"frames":frames},indent=2),encoding='utf-8')
print(json.dumps(checks))
