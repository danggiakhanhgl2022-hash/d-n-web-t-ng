"""Build a frame-accurate source viewer at requested 0.01s sample marks."""
import json, math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[1]
out=root/'frontend/public/motion-review';frames=out/'source';frames.mkdir(parents=True,exist_ok=True)
video=next(root.parent.glob('1794101442820*.mp4'))
cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
matrix=cv2.getPerspectiveTransform(np.float32([[66,505],[482,491],[494,711],[70,749]]),np.float32([[0,0],[479,0],[479,299],[0,299]]))
index=0
while True:
    ok,bgr=cap.read()
    if not ok:break
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    plane=cv2.warpPerspective(rgb,matrix,(480,300)) if index<1040 else cv2.resize(rgb,(169,300))
    Image.fromarray(plane).save(frames/f'f-{index:04d}.jpg',quality=90)
    index+=1
cap.release()
samples=[{'target':i/100,'frame':min(count-1,math.floor(i/100*fps+.5))} for i in range(math.ceil(count/fps*100))]
for sample in samples:sample['actual']=round(sample['frame']/fps,6)
(out/'source.json').write_text(json.dumps({'fps':fps,'frames':count,'samples':samples,'note':'Nearest actual source frame, no invented 100fps interpolation. Approximate fixed laptop crop.'},indent=2))
font=ImageFont.truetype(str(root/'frontend/public/fonts/Carlito-Regular.ttf'),18)
for second in range(7):
    sheet=Image.new('RGB',(1600,900),'#111811');draw=ImageDraw.Draw(sheet)
    for j in range(20):
        t=second+j*.05;f=min(count-1,math.floor(t*fps+.5));im=Image.open(frames/f'f-{f:04d}.jpg');im.thumbnail((320,195));x=j%5*320;y=j//5*225
        sheet.paste(im,(x,y+28));draw.text((x+5,y+3),f'{t:.2f}s / F{f}',font=font,fill='white')
    sheet.save(out/f'part-{second}.jpg',quality=92)
print(f'Built {len(samples)} 0.01s sample marks, {index} actual source images, 7 opening/transition contact sheets.')
