"""Read embedded glTF animation names and authored timeline track paths."""
import json,struct
from pathlib import Path

root=Path(__file__).resolve().parents[1]
assets=root/'frontend/public/renaissance/3d'
scenes=json.loads((assets/'scenes.json').read_text(encoding='utf-8'))
result={}
for scene in scenes:
 if scene['id'] not in {'sidekick','agentic','online','retail'}:continue
 state=json.loads((root/'frontend/public'/scene['timeline'].lstrip('/')).read_text(encoding='utf-8'))
 sheet=state['sheetsById']['Scene']
 entry={'timeline_objects':{},'assets':[]}
 for name,track in sheet['sequence']['tracksByObject'].items():
  paths=[json.loads(path) for path in track.get('trackIdByPropPath',{})]
  if name.startswith('asset') or name=='camera':entry['timeline_objects'][name]=paths
 for url in scene['assets']:
  if not url.endswith('.glb'):continue
  path=root/'frontend/public'/url.lstrip('/')
  raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
  data=json.loads(raw[20:20+length])
  entry['assets'].append({'file':path.name,'nodes':len(data.get('nodes',[])),'clips':[{'name':a.get('name'),'channels':len(a.get('channels',[]))} for a in data.get('animations',[])]})
 result[scene['id']]=entry
out=root/'runtime/verification/scene-motion-asset-inspection.json'
out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
for name,entry in result.items():
 print(name,[(a['file'],[x['name'] for x in a['clips']]) for a in entry['assets']])
print('Details written to runtime/verification/scene-motion-asset-inspection.json')
