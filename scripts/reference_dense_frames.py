"""Extract quarter-second evidence frames and timestamped contact sheets for review."""
from pathlib import Path
import json
import cv2
from PIL import Image,ImageDraw

root=Path(__file__).resolve().parents[1]
video=next(root.parent.glob('1794101442820*.mp4'))
out=root/'runtime/reference-video/dense';out.mkdir(parents=True,exist_ok=True)
capture=cv2.VideoCapture(str(video))
fps=capture.get(cv2.CAP_PROP_FPS);count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
records=[];frames=[]
for index in range(int(count/fps*4)):
    second=index/4
    capture.set(cv2.CAP_PROP_POS_MSEC,second*1000)
    ok,frame=capture.read()
    if not ok:continue
    image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    name=f't-{second:06.2f}.jpg';image.save(out/name,quality=85)
    records.append({'time_s':second,'frame_index':round(second*fps),'image':name})
    image.thumbnail((144,256));frames.append((second,image))
capture.release()
for offset in range(0,len(frames),24):
    sheet=Image.new('RGB',(864,4*282),'#151b17');draw=ImageDraw.Draw(sheet)
    for i,(second,image) in enumerate(frames[offset:offset+24]):
        x=i%6*144;y=i//6*282;sheet.paste(image,(x,y));draw.text((x+6,y+259),f'{second:05.2f} s',fill='#fff5df')
    sheet.save(out/f'contact-{offset//24+1:02d}.jpg',quality=90)
(out/'manifest.json').write_text(json.dumps({'video':video.name,'fps':fps,'source_frames':count,'interval_seconds':.25,'samples':records},indent=2),encoding='utf8')
print(json.dumps({'samples':len(records),'contact_sheets':(len(records)+23)//24,'interval_seconds':.25}))
