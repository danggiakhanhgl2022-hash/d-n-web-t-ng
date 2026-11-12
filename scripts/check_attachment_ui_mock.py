"""Exercise question attachment upload/removal against an in-memory mock API."""
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/'backend/app/questions.json').read_text(encoding='utf-8'))
project={'id':'qa-attachment','name':'Kiểm tra đính kèm','customer':'Giả lập','revision':1,'status':'DRAFT',
         'answers':[],'sources':[],'feedback':[],'approvals':[],'snapshots':[],'stage02':{},
         'validation':{'required_codes':['P2'],'active_groups':['P','A'],
                       'sections':[{'id':s['id'],'applicable':True,'total':sum(q['section']==s['id'] for q in catalog['questions']),'answered':0,'confirmed':0} for s in catalog['sections']]}}
requests=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900},reduced_motion='reduce')
    page.on('pageerror',lambda e:errors.append(str(e)))
    def route_api(route):
        req=route.request;url=urlsplit(req.url);path=url.path.split('/api/v1',1)[1]
        if path=='/auth/me':data={'user':{'id':'qa','username':'qa','display_name':'QA','role':'ADMIN','tenant_id':'qa'},'csrf_token':'qa-token'}
        elif path=='/projects':data={'items':[project]}
        elif path=='/questions':data=catalog
        elif path=='/projects/qa-attachment/sources' and req.method=='POST':
            body=req.post_data or ''
            requests.append({'method':'POST','csrf':req.headers.get('x-csrf-token'),'has_question':'P2' in body,'has_revision':'expected_revision' in body})
            project['revision']+=1
            project['sources'].append({'id':'file-1','filename':'mau.png','size':12,'question_code':'P2'})
            data=project
        elif path=='/projects/qa-attachment/sources/file-1' and req.method=='DELETE':
            requests.append({'method':'DELETE','csrf':req.headers.get('x-csrf-token'),'revision':parse_qs(url.query).get('expected_revision')})
            project['revision']+=1;project['sources']=[];data=project
        elif path=='/projects/qa-attachment':data=project
        else:data={}
        route.fulfill(status=200,content_type='application/json',body=json.dumps(data,ensure_ascii=False))
    page.route('**/api/v1/**',route_api)
    page.add_init_script("localStorage.setItem('video-os-project','qa-attachment')")
    page.goto('http://127.0.0.1:3100',wait_until='domcontentloaded')
    card=page.locator('[data-question-code="P2"]')
    expect(card).to_be_visible(timeout=30000)
    expect(card.locator('.attach')).to_be_visible()
    card.locator('input[type=file]').set_input_files({'name':'mau.png','mimeType':'image/png','buffer':b'fake-image-1'})
    expect(card.get_by_text('mau.png')).to_be_visible(timeout=10000)
    expect(card.get_by_role('button',name='Bỏ tệp mau.png')).to_be_visible(timeout=10000)
    card.get_by_role('button',name='Bỏ tệp mau.png').click()
    expect(card.get_by_text('mau.png')).to_have_count(0,timeout=10000)
    assert requests==[{'method':'POST','csrf':'qa-token','has_question':True,'has_revision':True},
                      {'method':'DELETE','csrf':'qa-token','revision':['2']}],requests
    assert not errors,errors
    browser.close()
print('PASS: mock upload and removal retain question code, CSRF and project revision; no real data used')
