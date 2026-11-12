"""Build evidence sheets. Run with the Python that has OpenCV and Pillow.

The laptop plane is an approximate crop for visual review, not a pixel metric.
"""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[1]
out=root/'runtime/verification/video-comparison'
before=root/'runtime/verification/visual-repair/before'
font=ImageFont.truetype(str(root/'frontend/public/fonts/Carlito-Regular.ttf'),20)
captures=json.loads((out/'recording.json').read_text(encoding='utf-8'))['captures']
times=(.25,.5,.75,1,1.5,2,3,4.25)
sheet=Image.new('RGB',(1040,len(times)*360),'#161b16')
draw=ImageDraw.Draw(sheet)
for row,t in enumerate(times):
    source=np.array(Image.open(root/f'runtime/reference-video/dense/t-{t:06.2f}.jpg').convert('RGB'))
    src=np.float32([[66,505],[482,491],[494,711],[70,749]])
    dest=np.float32([[0,0],[519,0],[519,324],[0,324]])
    crop=Image.fromarray(cv2.warpPerspective(source,cv2.getPerspectiveTransform(src,dest),(520,325)))
    record=next(c for c in captures if c['target_s']==t)
    web=Image.open(out/record['image']).convert('RGB').resize((520,325))
    y=row*360
    draw.text((12,y+4),f'Video mẫu {t:.2f}s · vùng màn hình ước lượng',font=font,fill='#fff5df')
    draw.text((532,y+4),f'Web đã sửa · thời gian thực {record["actual_s"]:.2f}s',font=font,fill='#fff5df')
    sheet.paste(crop,(0,y+35));sheet.paste(web,(520,y+35))
sheet.save(out/'source-vs-web.jpg',quality=92)

sheet=Image.new('RGB',(1440,980),'#161b16');draw=ImageDraw.Draw(sheet)
for row,t in enumerate((.75,7.)):
    record=next(c for c in captures if c['target_s']==t)
    old=Image.open(before/f'web-{t:05.2f}.png').convert('RGB').resize((720,450))
    new=Image.open(out/record['image']).convert('RGB').resize((720,450))
    y=row*490
    label='Mở vòng (ảnh minh họa, chưa căn trùng pose)' if row==0 else 'Cảnh ổn định: ánh sáng, tỷ lệ và form'
    draw.text((12,y+8),'TRƯỚC · '+label,font=font,fill='#fff5df')
    draw.text((732,y+8),'SAU · '+label,font=font,fill='#fff5df')
    sheet.paste(old,(0,y+40));sheet.paste(new,(720,y+40))
sheet.save(out/'before-after.jpg',quality=92)
print('Saved source-vs-web.jpg and before-after.jpg; approximate visual comparisons only')
