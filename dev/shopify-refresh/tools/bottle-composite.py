import sys, numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
# args: width cx cy angle warm bright out
W_T=int(sys.argv[1]); CX=float(sys.argv[2]); CY=float(sys.argv[3]); ANG=float(sys.argv[4]); WARM=float(sys.argv[5]); BRI=float(sys.argv[6]); OUT=sys.argv[7]
base=Image.open('pray/praying-with-frankincense-myrrh.jpg').convert('RGB')
cut=Image.open('bottle/fm-1oz-cutout.png').convert('RGBA').crop((313-6,91-6,592+7,828+7))
scale=W_T/279
cut=cut.resize((round(cut.width*scale), round(cut.height*scale)), Image.LANCZOS)
r,g,b,a=cut.split(); rgb=Image.merge('RGB',(r,g,b)); rgb=ImageEnhance.Brightness(rgb).enhance(BRI)
arr=np.asarray(rgb).astype(float); arr[...,1]*=(1-0.07*WARM); arr[...,2]*=(1-0.15*WARM)
w=arr.shape[1]; shade=np.linspace(0.82,1.02,w)[None,:,None]; arr=arr*shade
rgb=Image.fromarray(np.clip(arr,0,255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.75))
cut=Image.merge('RGBA',(*rgb.split(),a))
cut=cut.rotate(ANG, resample=Image.BICUBIC, expand=True)
px=round(CX-cut.width/2); py=round(CY-cut.height/2)
comp=base.copy(); comp.paste(cut,(px,py),cut)
fp=Image.new('L',base.size,0); fp.paste(cut.split()[3],(px,py)); fp=np.asarray(fp)>0
# occlusion zone: fingers of the right hand from y>=745 where x>=662 (tip slopes), everything from y>=800
Hh,Ww=fp.shape; yy,xx=np.mgrid[0:Hh,0:Ww]
zone=(yy>=800)|((xx>=662)&(yy>=745+np.clip((xx-662)*-0.0,0,0)))
hsv=np.asarray(base.convert('HSV')).astype(float); H=hsv[...,0]/255*360; S=hsv[...,1]/255; V=hsv[...,2]/255
skin=(H<40)&(S>0.28)&(S<0.6)&(V>0.4)&fp&zone
m=Image.fromarray((skin*255).astype('uint8')).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.0))
comp=Image.composite(base, comp, m)
comp.save(OUT, quality=94)
z=comp.crop((540,640,760,900)); z=z.resize((z.width*3,z.height*3), Image.LANCZOS); z.save(OUT.replace('.jpg','-zoom.png'))
print('saved', OUT, 'cut', cut.size, 'at', px, py)
