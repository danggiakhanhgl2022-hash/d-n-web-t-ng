"""Approximate source/candidate side-by-side evidence; not a registered pixel metric."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import cv2
import numpy as np

root=Path(__file__).resolve().parents[1]
out=root/'runtime/verification/effects-refinement'
font=ImageFont.truetype(str(root/'frontend/public/fonts/Carlito-Regular.ttf'),18)
sheet=Image.new('RGB',(1440,1320),'#171b16');draw=ImageDraw.Draw(sheet)
for row,t in enumerate([.1,.3,.5,.7]):
    frame=Image.open(root/f'runtime/reference-video/tenths/t-{6.1+t:04.1f}-full.jpg').convert('RGB')
    points=np.float32([[36,480],[539,470],[544,741],[32,750]])
    dst=np.float32([[0,0],[479,0],[479,299],[0,299]])
    source=Image.fromarray(cv2.warpPerspective(np.array(frame),cv2.getPerspectiveTransform(points,dst),(480,300)))
    a=Image.open(out/'round-1'/f'transition-{t:.1f}.jpg').resize((480,300))
    b=Image.open(out/'round-3'/f'transition-{t:.1f}.jpg').resize((480,300))
    y=row*330
    for x,img,label in [(0,source,f'Mẫu {6.1+t:.1f}s · crop ước lượng'),(480,a,f'Vòng 1 · +{t:.1f}s'),(960,b,f'Vòng 3 · +{t:.1f}s')]:
        draw.text((x+8,y+4),label,font=font,fill='#fff5df');sheet.paste(img,(x,y+30))
sheet.save(out/'transition-comparison.jpg',quality=93)
print('Saved transition-comparison.jpg')
