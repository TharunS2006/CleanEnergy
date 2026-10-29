import numpy as np, wave
SR=44100; D=60; n=SR*D; t=np.arange(n)/SR
rng=np.random.default_rng(3)
def env(t0,t1,a=2.0,r=2.0):
    e=np.zeros(n); i0,i1=int(t0*SR),int(t1*SR)
    seg=np.ones(i1-i0); na=int(a*SR); nr=int(r*SR)
    seg[:na]=np.linspace(0,1,na); seg[-nr:]=np.minimum(seg[-nr:],np.linspace(1,0,nr)); e[i0:i1]=seg; return e
def pad(freqs,t0,t1,gain,det=0.4):
    out=np.zeros(n)
    for f in freqs:
        for d in (-det,0,det):
            ph=rng.uniform(0,6.28); vib=0.003*np.sin(2*np.pi*0.25*t+ph)
            for h,a in ((1,1),(2,.35),(3,.15)):
                out+=a*np.sin(2*np.pi*(f+d)*h*t*(1+vib)+ph)
    return out*env(t0,t1,3,3)*gain/ (len(freqs)*3)
chords=[(110,164.8,220,277.2),(87.3,130.8,174.6,261.6),(98,146.8,196,246.9),(110,164.8,220,329.6)]
bed=sum(pad(c,i*15-1.5 if i else 0,min(60,(i+1)*15+1.5),1.0) for i,c in enumerate(chords))
# swell in scene 4
swell=pad((220,277.2,329.6,440),46,60,0.9)+pad((55,110),44,60,0.9)
wind=np.convolve(rng.normal(0,1,n),np.ones(300)/300,'same'); wind*=0.5+0.5*np.sin(2*np.pi*t/9+1)**2
bird=np.zeros(n)
def chirp(t0,f0,f1,dur=0.12,g=.5):
    i0=int(t0*SR); m=int(dur*SR); tt=np.arange(m)/SR
    f=np.linspace(f0,f1,m); ph=2*np.pi*np.cumsum(f)/SR
    s=np.sin(ph)*np.hanning(m)*g
    if i0+m<n: bird[i0:i0+m]+=s
for k in range(26):
    t0=rng.uniform(1,59)
    if 15<t0<30 and rng.random()<.7: continue
    f0=rng.uniform(2600,4200)
    for j in range(rng.integers(2,5)): chirp(t0+j*.16,f0+rng.uniform(-300,300),f0+rng.uniform(500,1500))
drop=np.zeros(n)
def plip(t0,g=.7):
    i0=int(t0*SR); m=int(.35*SR); tt=np.arange(m)/SR
    f=900*np.exp(-tt*6)+300; s=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tt*14)*g; drop[i0:i0+m]+=s
plip(26.4); plip(27.4,.25); plip(28.1,.12)
for tt in (21.0,23.5): plip(tt-0.0,.05)
mix=bed*0.26+swell*0.22+wind*0.045+bird*0.05+drop*0.5
mix*=np.clip(np.minimum(t/1.5,(D-t)/2.5),0,1)
L=mix+0.015*np.roll(mix,int(.018*SR)); R=mix+0.015*np.roll(mix,int(.027*SR))
m=max(abs(L).max(),abs(R).max()); st=np.stack([L,R],1)/m*0.85
w=wave.open('audio.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype('<i2').tobytes()); w.close(); print('ok')
