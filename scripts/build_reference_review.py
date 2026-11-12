"""Standalone local viewer for 387 original-video samples and observed phases."""
import json
import re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/'runtime/reference-video/tenths'
manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
source=(root/'frontend/app/referenceSequence.ts').read_text(encoding='utf-8')
chapters=[dict(id=m[0],start=float(m[1]),end=float(m[2]),paperAt=None if m[3]=='null' else float(m[3])) for m in re.findall(r"id:'([^']+)',start:([\d.]+),end:([\d.]+),paperAt:(null|[\d.]+)",source)]
intro=[
 'Nền tối, chữ nhỏ ở giữa; chưa mở tranh.',
 'Vẫn nền tối; chuẩn bị xuất hiện vùng sáng.',
 'Vùng tranh nhỏ mở phía trên tâm, mép phát sáng.',
 'Khối tranh xoay/mở rộng, nền trời và cây bắt đầu rõ.',
 'Mảng tranh mở rộng lệch, có phần mép sáng đứt đoạn.',
 'Vòng chiếm phần lớn chiều cao, khung chữ giữa rõ hơn.',
 'Mép tranh tiếp tục nở; biên trên trái lõm, không đều.',
 'Cảnh rộng hơn; camera tiếp tục lùi về bố cục hai bên.',
 'Mép tranh gần chạm biên; chi tiết người bắt đầu ở rìa.',
 'Tay áo đỏ đi vào từ phải, phần áo sáng từ trái.',
 'Tay/ống tay đỏ vươn ngang; nhân vật còn bị cắt ở mép.',
 'Đầu và thân người bên trái dần vào hình.',
 'Chân và giày bên trái hạ vào khung.',
 'Ván trượt gần dọc đi vào bên dưới chân.',
 'Hai nhân vật gần đủ; ván trượt còn nghiêng đứng.',
 'Camera ổn định dần, cánh tay hai bên còn hướng vào giữa.',
 'Ván trượt quay nghiêng; chân và vải dịch nhẹ.',
 'Ván trượt hạ gần ngang, người tiếp tục ổn định tư thế.',
 'Tay chân gần tư thế cuối; khung nội dung giữa rõ.',
 'Bố cục hai người ổn định; còn chuyển động nhỏ.',
 'Mục lục giữa đã hiện; ván trượt gần ngang.',
 'Ván trượt tiếp tục xoay nhẹ, đầu gối và vải trôi.',
 'Giữ bố cục hai bên, chuyển động nhỏ theo camera/rig.',
]
for sample in manifest['samples']:
    t=sample['second'];chapter=next((c for c in chapters if c['start']<=t<c['end']),None)
    sample['chapter']=chapter['id'] if chapter else 'video-outro'
    sample['phase']='màn kết TikTok' if not chapter else 'nội dung/thẻ đi lên' if chapter['paperAt'] is not None and t>=chapter['paperAt'] else 'tranh/camera/tiêu đề'
    sample['note']=intro[round(t*10)] if t<=2.2 else f"{sample['chapter']} · {sample['phase']}. Xem ảnh gốc để phân biệt cuộn trang với rung máy quay."
(out/'observations.json').write_text(json.dumps(dict(manifest,chapters=chapters),ensure_ascii=False,indent=2),encoding='utf-8')
html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Đối chiếu video từng 0,1 giây</title>
<style>*{box-sizing:border-box}body{margin:0;background:#171b16;color:#f8f1de;font:17px/1.6 system-ui}main{max-width:1200px;margin:auto;padding:28px}h1{font-size:30px}button,a{color:inherit}button{background:#30382d;border:1px solid #686e5f;padding:10px 16px;cursor:pointer}input[type=range]{width:100%;accent-color:#ff43af}section{display:grid;grid-template-columns:2fr 1fr;gap:24px;margin:24px 0}.image{background:#050705;min-height:350px;display:grid;place-items:center}.image img{max-width:100%;max-height:70vh;object-fit:contain}aside{padding:20px;border:1px solid #686e5f}strong{color:#ff85c7}.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}small{color:#bbb9aa}nav{display:flex;gap:8px;flex-wrap:wrap}nav button{font-size:13px;padding:6px 10px}@media(max-width:760px){section{grid-template-columns:1fr}main{padding:18px}.image{min-height:250px}}</style>
<main><h1>Video mẫu: từng bước 0,1 giây</h1><p>387 ảnh gốc · 30 fps · mỗi ảnh cách đúng 3 frame. Vùng website đã nắn phối cảnh gần đúng; không dùng để chấm phần trăm giống.</p>
<div class="controls"><button id="prev">−0,1 giây</button><button id="play">Phát ảnh 10 fps</button><button id="next">+0,1 giây</button><label><input type="checkbox" id="full">Xem nguyên khung quay</label><strong id="time"></strong></div>
<input id="scrub" aria-label="Mốc video theo phần mười giây" type="range" min="0" max="386" step="1" value="0">
<section><div class="image"><img id="frame" alt="Khung hình video gốc"></div><aside><strong id="chapter"></strong><p id="phase"></p><p id="note"></p><a id="original" target="_blank">Mở ảnh gốc</a><p><small>Ghi chú mở đầu được xem theo ảnh 0,1 giây. Nhãn các đoạn sau phân loại theo chương và điểm chuyển cảnh; không phải kết quả đo mọi khớp 3D.</small></p></aside></section><nav id="chapters"></nav></main>
<script>const DATA=__DATA__;let timer=null;const $=id=>document.getElementById(id);function show(n){n=Math.max(0,Math.min(DATA.samples.length-1,+n));$('scrub').value=n;const r=DATA.samples[n];$('frame').src=$('full').checked?r.full:r.ui;$('time').textContent=r.second.toFixed(1)+' s · frame '+r.frame_index;$('chapter').textContent=r.chapter;$('phase').textContent=r.phase;$('note').textContent=r.note;$('original').href=r.full;for(let i=n+1;i<Math.min(n+4,DATA.samples.length);i++){const img=new Image;img.src=DATA.samples[i][$('full').checked?'full':'ui'];}}$('scrub').oninput=e=>show(e.target.value);$('full').onchange=()=>show($('scrub').value);$('prev').onclick=()=>show(+$('scrub').value-1);$('next').onclick=()=>show(+$('scrub').value+1);$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('play').textContent='Phát ảnh 10 fps';return}timer=setInterval(()=>{if(+$('scrub').value>=386){clearInterval(timer);timer=null;$('play').textContent='Phát ảnh 10 fps';return}show(+$('scrub').value+1)},100);$('play').textContent='Dừng'};for(const c of DATA.chapters){const b=document.createElement('button');b.textContent=c.id+' · '+c.start+'s';b.onclick=()=>show(Math.round(c.start*10));$('chapters').append(b)}show(0);</script></html>'''
html=html.replace('__DATA__',json.dumps(dict(samples=manifest['samples'],chapters=chapters),ensure_ascii=False).replace('</','<\\/'))
(out/'index.html').write_text(html,encoding='utf-8')
print('Saved 387 annotated samples, observations.json and standalone index.html')
