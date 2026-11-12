"""Sample the recording at 0.05s; preserve actual 30fps frame timestamps."""
import json, math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parents[1]
video=next(root.parent.glob('1794101442820*.mp4'))
out=root/'runtime/reference-video/twentieths';out.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
transform=cv2.getPerspectiveTransform(np.float32([[66,505],[482,491],[494,711],[70,749]]),np.float32([[0,0],[479,0],[479,299],[0,299]]))
font=ImageFont.truetype(str(root/'frontend/public/fonts/Carlito-Regular.ttf'),17)
rows=[]
for i in range(math.ceil(count/fps*20)):
    target=i/20;frame=min(count-1,math.floor(target*fps+.5))
    cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,bgr=cap.read()
    if not ok:break
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    full=f't-{target:05.2f}-full.jpg';ui=f't-{target:05.2f}-ui.jpg'
    Image.fromarray(rgb).save(out/full,quality=90)
    plane=cv2.warpPerspective(rgb,transform,(480,300)) if frame<1040 else cv2.resize(rgb,(169,300))
    Image.fromarray(plane).save(out/ui,quality=92)
    rows.append(dict(target=target,actual=round(frame/fps,6),frame=frame,full=full,ui=ui))
cap.release()
for start in range(0,len(rows),20):
    sheet=Image.new('RGB',(1600,900),'#151b17');draw=ImageDraw.Draw(sheet)
    for j,row in enumerate(rows[start:start+20]):
        im=Image.open(out/row['ui']);im.thumbnail((320,195));x=j%5*320;y=j//5*225
        sheet.paste(im,(x+(320-im.width)//2,y+28))
        draw.text((x+6,y+3),f'{row["target"]:.2f}s / F{row["frame"]} / {row["actual"]:.3f}s',font=font,fill='#fff5df')
    sheet.save(out/f'contact-{start//20:02d}.jpg',quality=93)
(out/'manifest.json').write_text(json.dumps(dict(fps=fps,source_frames=count,interval=.05,note='Nearest source frame, no invented interpolation. Fixed approximate screen crop, not registered similarity.',samples=rows),indent=2),encoding='utf-8')
print(f'Extracted {len(rows)} samples and {(len(rows)+19)//20} contact sheets at requested 0.05s intervals; actual source frame times retained.')
