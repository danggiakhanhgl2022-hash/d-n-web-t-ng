"""Record a scheduled scroll walkthrough; retain real capture times."""
import base64,json,re
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1];out=root/'frontend/public/motion-review/walk';out.mkdir(parents=True,exist_ok=True)
text=(root/'frontend/app/referenceSequence.ts').read_text(encoding='utf-8')
parts=[{'id':m[0],'start':float(m[1]),'paper':None if m[2]=='null' else float(m[2])} for m in re.findall(r"id:'([^']+)',start:([\d.]+),end:[^,]+,paperAt:(null|[\d.]+)",text)]
shots=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''window.reviewEpoch=0;window.reviewStates=[];function tick(t){const root=document.querySelector('.renaissance-cinema');const opening=root?+getComputedStyle(root).getPropertyValue('--opening'):0;if(!reviewEpoch&&opening>0&&opening<1)reviewEpoch=performance.timeOrigin+t-opening*3200;if(reviewEpoch){const c=document.querySelector('canvas');reviewStates.push({time:(performance.timeOrigin+t-reviewEpoch)/1000,status:root?.dataset.status,scene:c?.dataset.scene});}requestAnimationFrame(tick)}requestAnimationFrame(tick);''')
    cdp=page.context.new_cdp_session(page)
    def frame(event):
        name=f'frame-{len(shots):05d}.jpg';(out/name).write_bytes(base64.b64decode(event['data']))
        shots.append({'timestamp':event['metadata']['timestamp'],'image':name})
        cdp.send('Page.screencastFrameAck',{'sessionId':event['sessionId']})
    cdp.on('Page.screencastFrame',frame)
    cdp.send('Page.startScreencast',{'format':'jpeg','quality':82,'maxWidth':960,'maxHeight':600,'everyNthFrame':1})
    page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
    page.wait_for_function('window.reviewEpoch>0',timeout=25000)
    page.evaluate('''parts=>{document.documentElement.style.scrollBehavior='auto';let closed=false;window.walkTimer=setInterval(()=>{const t=(performance.timeOrigin+performance.now()-reviewEpoch)/1000;if(t>3.6&&!closed){const d=document.querySelector('.cinema-login-dialog[open]');if(d){d.querySelector('.cinema-dialog-close')?.click();closed=true}}if(t<parts[1].start)return;let i=0;for(let j=0;j<parts.length;j++)if(t>=parts[j].start)i=j;const panels=[...document.querySelectorAll('.cinema-chapter')],panel=panels[i];if(!panel)return;const top=e=>e.getBoundingClientRect().top+scrollY;const begin=top(panel),end=panels[i+1]?top(panels[i+1]):begin+panel.offsetHeight-innerHeight;const paper=panel.querySelector('.cinema-paper');const middle=paper?Math.max(begin,top(paper)-innerHeight*.75):end;const stop=parts[i+1]?.start??(1040/30);const at=parts[i].paper;let y;if(at&&t<at)y=begin+(middle-begin)*Math.max(0,Math.min(1,(t-parts[i].start)/(at-parts[i].start)));else if(at)y=middle+(end-middle)*Math.max(0,Math.min(1,(t-at)/(stop-at)));else y=begin;scrollTo({top:y,behavior:'instant'});},30)}''',parts)
    page.wait_for_function('(performance.timeOrigin+performance.now()-reviewEpoch)/1000>34.67',timeout=45000)
    page.evaluate('clearInterval(walkTimer)');cdp.send('Page.stopScreencast')
    epoch=page.evaluate('reviewEpoch')/1000;states=page.evaluate('reviewStates')
    for shot in shots:shot['actual']=round(shot.pop('timestamp')-epoch,4)
    (out/'recording.json').write_text(json.dumps({'captures':shots,'errors':errors,'states':states,'note':'Automatic login is dismissed by the audit at 3.6s. Programmatic scroll reconstruction, not a measurement of original scroll input. No website TikTok outro.'},indent=2))
    browser.close()
assert not errors,errors
seen=sorted(set(x.get('scene') for x in states if x.get('scene')))
print(json.dumps({'captured_frames':len(shots),'scenes_seen':seen,'errors':errors}))
