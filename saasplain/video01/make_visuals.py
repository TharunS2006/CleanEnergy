import sys, subprocess, os
from PIL import Image, ImageDraw, ImageFont
OUT=sys.argv[1]
B="/usr/share/fonts/opentype/inter/Inter-Bold.otf"; M="/usr/share/fonts/opentype/inter/Inter-Medium.otf"
if not os.path.exists(B):
    import glob; B=[f for f in glob.glob("/usr/share/fonts/opentype/inter/*.otf") if f.endswith("Inter-Bold.otf") or "Inter-Bold" in f][0]
IND=(79,70,229); TEAL=(20,184,166); CH=(31,41,55); WW=(250,250,247); GR=(156,163,175); RED=(239,68,68)
F=lambda p,s: ImageFont.truetype(p,s)
def box(d,xy,txt,fill,fg,font,r=28,outline=None):
    d.rounded_rectangle(xy,r,fill=fill,outline=outline,width=6)
    x0,y0,x1,y1=xy; w=d.textlength(txt,font=font)
    d.text(((x0+x1-w)/2,(y0+y1)/2),txt,font=font,fill=fg,anchor="lm")
def arrow(d,x0,y,x1,c,w=10):
    d.line([(x0,y),(x1-28,y)],fill=c,width=w); d.polygon([(x1,y),(x1-34,y-22),(x1-34,y+22)],fill=c)
# ---- Thumbnail 1280x720
im=Image.new("RGB",(1280,720),CH); d=ImageDraw.Draw(im)
d.text((70,70),"AI AGENTS",font=F(B,130),fill=WW)
d.text((70,215),"Explained",font=F(B,130),fill=IND)
steps=[("Goal",GR),("Tools",IND),("Action",TEAL)]
x=70
for i,(t,c) in enumerate(steps):
    box(d,(x,450,x+300,590),t,c,WW,F(B,58)); 
    if i<2: arrow(d,x+305,520,x+395,WW)
    x+=400
d.rounded_rectangle((1010,70,1210,170),20,fill=RED); d.text((1110,120),"vs CHAT",font=F(B,40),fill=WW,anchor="mm")
d.text((70,640),"saasplain",font=F(M,36),fill=GR)
im.save(f"{OUT}/thumbnail.png")
# ---- Animated diagram 1920x1080, 30fps, 12s
steps=["Instructions","Tool selection","Approval","Action","Result"]
cols=[GR,IND,(124,58,237),TEAL,(34,197,94)]
fps=30; N=12*fps; fr=f"{OUT}/frames"; os.makedirs(fr,exist_ok=True)
W,H=1920,1080; bw,bh,gap=300,150,64; x0=(W-(5*bw+4*gap))//2; y=470
ft=F(B,40); fh=F(B,72); fs=F(M,36)
for n in range(N):
    t=n/fps
    im=Image.new("RGB",(W,H),WW); d=ImageDraw.Draw(im)
    d.text((W/2,170),"How an AI agent works",font=fh,fill=CH,anchor="mm")
    for i,s in enumerate(steps):
        start=1+i*1.6; a=max(0,min(1,(t-start)/0.5))
        if a<=0: continue
        x=x0+i*(bw+gap); dy=int((1-a)*40)
        c=tuple(int(WW[k]+(cols[i][k]-WW[k])*a) for k in range(3))
        d.rounded_rectangle((x,y+dy,x+bw,y+bh+dy),26,fill=c)
        d.text((x+bw/2,y+bh/2+dy),s,font=ft,fill=WW,anchor="mm")
        d.text((x+bw/2,y-40+dy),f"Step {i+1}",font=fs,fill=GR,anchor="mm")
        if i<4 and t>start+0.6:
            p=min(1,(t-start-0.6)/0.5); ax=x+bw+6; ex=ax+int((gap-12)*p)
            if ex-ax>30: arrow(d,ax,y+bh//2,ex,CH,8)
    if t>9.2:
        a=min(1,(t-9.2)/0.6); c=tuple(int(WW[k]+(CH[k]-WW[k])*a) for k in range(3))
        d.text((W/2,820),"A chatbot answers. An agent acts.",font=F(B,56),fill=c,anchor="mm")
    d.text((W-60,H-50),"saasplain",font=fs,fill=GR,anchor="rm")
    im.save(f"{fr}/{n:04d}.png")
subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(fps),"-i",f"{fr}/%04d.png","-c:v","libx264","-pix_fmt","yuv420p","-crf","20",f"{OUT}/agent_flow.mp4"],check=True)
subprocess.run(["rm","-rf",fr])
