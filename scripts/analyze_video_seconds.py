"""Extract original-video evidence at every whole second, with approximate UI crops."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[1]
video=next(root.parent.glob('1794101442820*.mp4'))
out=root/'runtime/reference-video/seconds'
out.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(str(video))
fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));duration=count/fps
font=ImageFont.truetype(str(root/'frontend/public/fonts/Carlito-Regular.ttf'),20)
records=[]
for second in range(int(duration)+1):
    cap.set(cv2.CAP_PROP_POS_FRAMES,round(second*fps));ok,bgr=cap.read()
    if not ok:continue
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(out/f'second-{second:02d}-full.jpg',quality=93)
    src=np.float32([[66,505],[482,491],[494,711],[70,749]])
    dst=np.float32([[0,0],[383,0],[383,239],[0,239]])
    crop=Image.fromarray(cv2.warpPerspective(rgb,cv2.getPerspectiveTransform(src,dst),(384,240))) if second<35 else Image.fromarray(rgb).resize((135,240))
    canvas=Image.new('RGB',(384,270),'#151b17');canvas.paste(crop,((384-crop.width)//2,30))
    ImageDraw.Draw(canvas).text((10,4),f'{second:02d}s · '+('Vùng website (ước lượng)' if second<35 else 'Màn kết video'),font=font,fill='#fff5df')
    canvas.save(out/f'second-{second:02d}-ui.jpg',quality=93)
    records.append({'second':second,'frame':round(second*fps),'full':f'second-{second:02d}-full.jpg','ui':f'second-{second:02d}-ui.jpg'})
cap.release()
for start in range(0,len(records),12):
    sheet=Image.new('RGB',(1536,810),'#151b17')
    for i,record in enumerate(records[start:start+12]):
        sheet.paste(Image.open(out/record['ui']),((i%4)*384,(i//4)*270))
    sheet.save(out/f'seconds-{start:02d}-{min(start+11,len(records)-1):02d}.jpg',quality=94)
(out/'manifest.json').write_text(json.dumps({'video':video.name,'fps':fps,'frames':count,'duration_s':duration,'crop':'approximate fixed laptop plane; inspect full frames for precise judgments','samples':records},indent=2),encoding='utf-8')
print(json.dumps({'seconds':len(records),'duration_s':duration,'fps':fps}))
