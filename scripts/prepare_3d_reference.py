"""Cache public reference scene assets locally with provenance; never run remote app code."""
import json,hashlib,urllib.request,concurrent.futures,shutil
from pathlib import Path
root=Path('runtime/reference-video');dest=Path('frontend/public/renaissance/3d');dest.mkdir(parents=True,exist_ok=True)
data=json.loads((root/'decoded-data.json').read_text(encoding='utf8'))
scenes=[]
def walk(x):
    if isinstance(x,dict):
        if x.get('backgroundAnimation') and x.get('backgroundAssets'):
            scenes.append(x)
        else:
            for v in x.values():walk(v)
    elif isinstance(x,list):
        for v in x:walk(v)
walk(data)
jobs={};configs=[]
def local(url):
    name=url.split('/')[-1].split('?')[0]
    jobs[name]=url
    return '/renaissance/3d/'+name
for scene in scenes:
    name=scene.get('handle','hero')
    configs.append({'id':name,'title':scene.get('title','The Production Edition'),'timeline':local(scene['backgroundAnimation']['url']),'assets':[local(a['url']) for a in scene['backgroundAssets']], 'fallback':local(scene['fallbackImage']['url']), 'customCamera':scene.get('customCameraName')})
configs.sort(key=lambda c:0 if c['id']=='hero' else 1)
def download(item):
    name,url=item;target=dest/name
    if not target.exists():target.write_bytes(urllib.request.urlopen(url,timeout=60).read())
    return {'file':name,'source':url,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:manifest=list(pool.map(download,jobs.items()))
for config in configs:
    for asset in config['assets']:
        path=dest/asset.split('/')[-1]
        if path.suffix!='.json':continue
        descriptor=json.loads(urllib.request.urlopen(jobs[path.name],timeout=60).read())
        for key in ('url','fallbackImage'):
            if descriptor.get(key):
                remote=descriptor[key];descriptor[key]=local(remote)
                manifest.append(download((descriptor[key].split('/')[-1],remote)))
        path.write_text(json.dumps(descriptor),encoding='utf8')
(dest/'scenes.json').write_text(json.dumps(configs,indent=2),encoding='utf8')
for item in manifest:item['cached_sha256']=hashlib.sha256((dest/item['file']).read_bytes()).hexdigest()
Path('docs/REFERENCE-3D-ASSETS.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
for folder,names in [('basis',['basis_transcoder.js','basis_transcoder.wasm']),('draco/gltf',['draco_decoder.js','draco_decoder.wasm','draco_wasm_wrapper.js'])]:
    source=Path('frontend/node_modules/three/examples/jsm/libs')/folder
    target=dest/folder;target.mkdir(parents=True,exist_ok=True)
    for name in names:shutil.copy2(source/name,target/name)
print(json.dumps({'scenes':len(configs),'assets':len(manifest),'bytes':sum(x['bytes'] for x in manifest)}))
