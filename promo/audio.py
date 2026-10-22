# موسيقى وساوند إفكت مولّدة بالكامل (بدون حقوق) ومتزامنة مع أحداث المشهد
import sys, json, wave, numpy as np
SR=44100; DUR=15.0; N=int(SR*DUR)
ev=json.load(open(sys.argv[1])); OUT=sys.argv[2]
rng=np.random.default_rng(7)
L=np.zeros(N); R=np.zeros(N)
def t_(d): return np.arange(int(SR*d))/SR
def add(sig,at,g=1.0,pan=0.0):
    i=int(at*SR); 
    if i>=N: return
    sig=sig[:N-i]; L[i:i+len(sig)]+=sig*g*(1-pan)**.5*1.0; R[i:i+len(sig)]+=sig*g*(1+pan)**.5*1.0
def lp(x,a):  # one-pole lowpass
    y=np.empty_like(x); s=0.0; a=np.broadcast_to(np.asarray(a,float),x.shape)
    for i in range(len(x)): s+=a[i]*(x[i]-s); y[i]=s
    return y
def hz(n): return 440*2**((n-69)/12)
def env(d,a=.005,r=None):
    t=t_(d); e=np.minimum(1,t/a)
    return e*np.exp(-t/(r or d/4))
# ---------- music: 116 BPM, C major-ish, progression C–G–Am–F ----------
BPM=116; B=60/BPM
prog=[(48,[60,64,67,72]),(43,[59,62,67,71]),(45,[60,64,69,72]),(41,[60,65,69,72])]
def pad(notes,d):
    t=t_(d); x=sum(np.sin(2*np.pi*hz(n)*t*k)/k**1.4 for n in notes for k in (1,2,3))*(1+0*t)
    x+=sum(np.sin(2*np.pi*hz(n)*1.003*t) for n in notes)*.5
    e=np.minimum(1,t/.35)*np.minimum(1,(d-t)/.3); return x*e/len(notes)
def pluck(n,d=.32):
    t=t_(d); x=np.sin(2*np.pi*hz(n)*t)+.35*np.sin(2*np.pi*hz(n)*2*t)+.12*np.sin(2*np.pi*hz(n)*3*t); return x*env(d,.002,.09)
def bass(n,d):
    t=t_(d); x=np.sin(2*np.pi*hz(n)*t)+.25*np.sin(2*np.pi*hz(n)*2*t); return x*env(d,.004,d/2.5)
def kick():
    t=t_(.35); f=50+110*np.exp(-t/.035); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/.11)
def hat(d=.05):
    x=rng.standard_normal(int(SR*d)); x=x-lp(x,.35); return x*env(d,.001,.012)
def clap():
    x=rng.standard_normal(int(SR*.18)); x=lp(x,.5)-lp(x,.08); e=np.exp(-t_(.18)/.045)
    for o in (.0,.011,.022): e[int(o*SR):]+=0
    return x*e
MEND=13.0  # الدرامز بتوقف عند الخاتمة وبيضل كورد طويل
bar=4*B; nb=int(np.ceil(DUR/bar))
for b in range(nb):
    t0=b*bar; root,ch=prog[b%4]
    if t0<MEND: add(pad(ch,min(bar,MEND-t0)+.3),t0,.10)
    for k in range(8):
        tt=t0+k*B/2
        if tt>=MEND: break
        add(pluck(ch[[0,2,1,3,2,1,3,2][k]]+12,.3),tt,.07 if tt<2.6 else .11,pan=(-.4 if k%2 else .4))
        if tt>=2.6:   # الإيقاع بيدخل مع أول خطوة
            if k%2==0: add(kick(),tt,.55); add(bass(root,B*.9),tt,.22)
            else: add(hat(),tt,.10,pan=.2)
            if k in (2,6): add(clap(),tt,.16)
        else:
            if k%2==0: add(bass(root,B*.9),tt,.12)
# كورد الخاتمة
t=t_(2.0); fin=pad([60,64,67,72,76],2.0)*np.exp(-t/1.2); add(fin,MEND,.16)
add(bass(36,2.0),MEND,.3)
# ---------- SFX ----------
def tapfx():
    t=t_(.06); return (np.sin(2*np.pi*1900*t)*.6+np.sin(2*np.pi*950*t))*np.exp(-t/.012)
def keyfx():
    x=rng.standard_normal(int(SR*.03)); x=x-lp(x,.3); t=t_(.03); return x*np.exp(-t/.006)*.7+np.sin(2*np.pi*rng.uniform(1100,1500)*t)*np.exp(-t/.008)*.4
def popfx():
    t=t_(.14); f=420+700*(t/.14)**.6; return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/.05)
def whoosh(d=.55):
    x=rng.standard_normal(int(SR*d)); t=t_(d); sh=np.sin(np.pi*t/d)**2
    lo=lp(x,.02+.25*sh); return (lo-lp(lo,.01))*sh*2.2
def bell(n,d=1.2):
    t=t_(d); f=hz(n); return (np.sin(2*np.pi*f*t)+.4*np.sin(2*np.pi*f*2.76*t)*np.exp(-t/.15)+.25*np.sin(2*np.pi*f*5.4*t)*np.exp(-t/.06))*env(d,.002,.35)
def riser(d=.6):
    x=rng.standard_normal(int(SR*d)); t=t_(d); return (x-lp(x,.05))*(t/d)**2.5*.6
def boom():
    t=t_(1.4); f=38+50*np.exp(-t/.08); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/.45)
for name,ms in ev:
    at=ms/1000
    if name=='tap':    add(tapfx(),at,.45)
    elif name=='key':  add(keyfx(),at,.35,pan=rng.uniform(-.2,.2))
    elif name=='pop':  add(popfx(),at,.45); add(bell(84,.5),at+.06,.12)
    elif name=='whoosh': add(whoosh(),at-.22,.30)
    elif name=='success':
        for k,n in enumerate((76,79,84)): add(bell(n),at+k*.09,.20)
    elif name=='impact':
        add(riser(),at-.6,.5); add(boom(),at,.65); add(whoosh(.8),at-.2,.25)
# ---------- reverb صغير + ماستر ----------
def verb(x):
    y=x.copy()
    for dl,g in ((.029,.35),(.037,.3),(.041,.27),(.053,.22)):
        d=int(dl*SR); z=np.zeros_like(x); 
        for r in range(6): 
            o=d*(r+1)
            if o<len(x): z[o:]+=x[:-o]*g**(r+1)
        y+=z*.5
    return y
L=verb(L); R=verb(R)
m=np.stack([L,R],1)
fade=np.ones(N); fl=int(.6*SR); fade[-fl:]=np.linspace(1,0,fl); fade[:int(.03*SR)]=np.linspace(0,1,int(.03*SR))
m*=fade[:,None]
m=np.tanh(m*1.2)/np.tanh(1.2); m/=np.abs(m).max()/0.89
w=wave.open(OUT,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((m*32767).astype('<i2').tobytes()); w.close()
print('audio ok', OUT)
