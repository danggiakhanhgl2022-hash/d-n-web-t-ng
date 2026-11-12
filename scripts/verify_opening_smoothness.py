"""Read-only repeated opening test; rAF responsiveness and actual pose update cadence."""
import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
label=sys.argv[1] if len(sys.argv)>1 else 'current'
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for run in range(3):
        context=browser.new_context(viewport={'width':1366,'height':768})
        page=context.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_init_script('''
        window.__openingTest={frames:[],poses:[],longTasks:[]};
        try{new PerformanceObserver(list=>{for(const e of list.getEntries())window.__openingTest.longTasks.push({at:e.startTime,ms:e.duration})}).observe({type:'longtask',buffered:true})}catch{}
        let last=0,pose='',poseAt=0;
        function measure(t){
          const canvas=document.querySelector('.cinema-webgl canvas');
          const current=canvas?.dataset.timeline;
          const ready=document.querySelector('.renaissance-cinema')?.dataset.status==='ready';
          if(last)window.__openingTest.frames.push({at:t,ms:t-last,ready});last=t;
          if(ready&&current!==undefined&&current!==pose){if(poseAt)window.__openingTest.poses.push({at:t,ms:t-poseAt});pose=current;poseAt=t}
          requestAnimationFrame(measure);
        }requestAnimationFrame(measure);
        ''')
        page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
        page.wait_for_timeout(12000)
        raw=page.evaluate('window.__openingTest')
        canvas_sources=[]
        for resource in page.evaluate("performance.getEntriesByType('resource').map(e=>e.name).filter(n=>n.includes('/_next/')&&n.includes('.js'))"):
            content=page.request.get(resource).text()
            if 'rigPose' in content:canvas_sources.append(resource)
        def stats(values):
            values=sorted(values)
            return {'count':len(values),'p50_ms':round(values[len(values)//2],2) if values else None,'p95_ms':round(values[min(len(values)-1,int(len(values)*.95))],2) if values else None,'over_100ms':sum(v>100 for v in values)}
        first_pose=raw['poses'][0]['at'] if raw['poses'] else 0
        poses=[x['ms'] for x in raw['poses'] if first_pose+500<x['at']<first_pose+6000]
        result={'run':run+1,'served_canvas_bundles':canvas_sources,'active_build':json.loads(Path('runtime/frontend-build.json').read_text()),'raf_ready':stats([x['ms'] for x in raw['frames'] if x['ready']]),'camera_update':stats(poses),'long_tasks':raw['longTasks'],'status':page.locator('.renaissance-cinema').get_attribute('data-status'),'errors':errors}
        results.append(result);context.close()
    browser.close()
out=Path('runtime/verification/opening-performance');out.mkdir(parents=True,exist_ok=True)
(out/f'{label}.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps(results))
