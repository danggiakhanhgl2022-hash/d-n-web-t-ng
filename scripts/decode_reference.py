import json,re,urllib.request
from pathlib import Path
root=Path('runtime/reference-video')
s=(root/'shopify-reference.html').read_text(encoding='utf8')
start=s.find('enqueue(')
print(s[start:start+180])
urls=sorted(set(u.replace('\\u0026','&') for u in re.findall(r'https[^\s"<>\\]+',s)))
assets=[u for u in urls if any(x in u for x in ('.glb','.ktx2','.theatre-project-state','.woff'))]
(root/'scene-assets.json').write_text(json.dumps(assets,indent=2),encoding='utf8')
print(json.dumps(assets,indent=2))
encoded=json.JSONDecoder().raw_decode(s[start+len('enqueue('):])[0]
values=json.loads(encoded)
cache={}
def decode(i):
    if i<0:return None
    if i in cache:return cache[i]
    value=values[i]
    if isinstance(value,dict):
        result={};cache[i]=result
        for k,v in value.items():result[str(decode(int(k[1:])))] = decode(v)
        return result
    if isinstance(value,list):
        result=[];cache[i]=result
        result.extend(decode(v) if isinstance(v,int) else v for v in value)
        return result
    return value
data=decode(0)
(root/'decoded-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print('Decoded data saved')
