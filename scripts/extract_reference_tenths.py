"""Extract every third frame of the 30fps reference: exact 0.1-second spacing."""
import csv
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[1]
video=next(root.parent.glob('1794101442820*.mp4'))
out=root/'runtime/reference-video/tenths';out.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
assert abs(fps-30)<.01,fps
font=ImageFont.truetype(str(root/'frontend/public/fonts/Carlito-Regular.ttf'),17)
src=np.float32([[66,505],[482,491],[494,711],[70,749]])
dest=np.float32([[0,0],[479,0],[479,299],[0,299]])
transform=cv2.getPerspectiveTransform(src,dest)
rows=[];frame_index=0
while True:
    ok,bgr=cap.read()
    if not ok:break
    if frame_index%3==0:
        second=frame_index/fps
        rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        full=f't-{second:04.1f}-full.jpg';ui=f't-{second:04.1f}-ui.jpg'
        Image.fromarray(rgb).save(out/full,quality=91)
        plane=cv2.warpPerspective(rgb,transform,(480,300)) if second<34.75 else cv2.resize(rgb,(169,300))
        Image.fromarray(plane).save(out/ui,quality=92)
        region=plane[20:275,65:440] if second<34.75 else plane
        hsv=cv2.cvtColor(region,cv2.COLOR_RGB2HSV)
        lit=((hsv[:,:,2]>65)&((hsv[:,:,1]>25)|(hsv[:,:,2]>160)))
        rows.append(dict(second=round(second,1),frame_index=frame_index,full=full,ui=ui,approx_lit_fraction=round(float(lit.mean()),5)))
    frame_index+=1
cap.release()
for start in range(0,len(rows),10):
    sheet=Image.new('RGB',(1600,450),'#151b17');draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(rows[start:start+10]):
        image=Image.open(out/r['ui']);image.thumbnail((320,200))
        x=i%5*320;y=i//5*225
        sheet.paste(image,(x+(320-image.width)//2,y+25))
        draw.text((x+8,y+3),f'{r["second"]:04.1f}s · frame {r["frame_index"]}',font=font,fill='#fff5df')
    sheet.save(out/f'contact-{start//10:02d}.jpg',quality=92)
with (out/'opening-measurements.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['second','frame_index','approx_lit_fraction']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in rows if r['second']<=3.5)
(out/'manifest.json').write_text(json.dumps({'video':video.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'fps':fps,'source_frames':count,'interval_s':.1,'samples':rows,'crop_note':'Fixed approximate laptop plane. Aperture fractions are diagnostics, not similarity scores.'},indent=2),encoding='utf-8')
print(json.dumps({'samples':len(rows),'contact_sheets':(len(rows)+9)//10,'fps':fps,'first':rows[0]['second'],'last':rows[-1]['second']}))
