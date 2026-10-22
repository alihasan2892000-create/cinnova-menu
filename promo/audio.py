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
MEND=next((ms/1000 for n,ms in ev if n=="impact"),13.0)  # الدرامز بتوقف عند الخاتمة وبيضل كورد طويل
bar=4*B; nb=int(np.ceil(DUR/bar))
for b in range(nb):
    t0=b*bar; root,ch=prog[b%4]
    if t0<MEND: add(pad(ch,min(bar,MEND-t0)+.3),t0,.10)
    for k in range(8):
        tt=t0+k*B/2
        if tt>=MEND: break
        add(pluck(ch[[0,2,1,3,2,1,3,2][k]]+12,.3),tt,.07 if tt<2.6 else .11,pan=(-.4 if k%2 else .4))
        if tt>=2.6:   # الإيقاع بيدخل مع أول خطوة
            if k%2==0: add(kick(),tt,.38); add(bass(root,B*.9),tt,.22)
            else: add(hat(),tt,.05,pan=.2)
            if k in (2,6): add(clap(),tt,.07)
        else:
            if k%2==0: add(bass(root,B*.9),tt,.12)
# كورد الخاتمة
FD=DUR-MEND; t=t_(FD); fin=pad([60,64,67,72,76],FD)*np.exp(-t/1.6); add(fin,MEND,.16)
add(bass(36,FD),MEND,.3)
# ---------- SFX (ناعمة وخفيفة) ----------
def soft(d,a,r): # إنفلوب بهجوم ناعم بدل الطقة الحادة
    t=t_(d); return np.minimum(1,t/a)**2*np.exp(-t/r)
def tapfx():   # "توك" خشبي ناعم
    t=t_(.09); return (np.sin(2*np.pi*620*t)+.3*np.sin(2*np.pi*1240*t))*soft(.09,.004,.022)
def keyfx():   # نقرة كيبورد خفيفة جداً
    t=t_(.04); x=lp(rng.standard_normal(len(t)),.18); return (x*.5+np.sin(2*np.pi*rng.uniform(900,1100)*t)*.5)*soft(.04,.002,.008)
def popfx():   # فقاعة ناعمة
    t=t_(.16); f=380+320*(t/.16)**.5; return np.sin(2*np.pi*np.cumsum(f)/SR)*soft(.16,.008,.045)
def whoosh(d=.75):  # نسمة هوا بدل الووش القوي
    x=rng.standard_normal(int(SR*d)); t=t_(d); sh=np.sin(np.pi*t/d)**3
    lo=lp(lp(x,.015+.06*sh),.05); return (lo-lp(lo,.004))*sh*3.0
def bell(n,d=1.4):
    t=t_(d); f=hz(n); return (np.sin(2*np.pi*f*t)+.18*np.sin(2*np.pi*f*2*t)*np.exp(-t/.25))*soft(d,.006,.45)
def swell(d=.9):  # صعود ناعم قبل الخاتمة
    x=lp(rng.standard_normal(int(SR*d)),.04); t=t_(d); return x*(t/d)**2*1.2
def bloom():      # بدل البوم: نغمة دافية بتفتح
    t=t_(2.2); return (np.sin(2*np.pi*hz(48)*t)*.6+np.sin(2*np.pi*hz(60)*t)*.4)*np.minimum(1,t/.08)*np.exp(-t/.9)
for name,ms in ev:
    at=ms/1000
    if name=='tap':    add(tapfx(),at,.16)
    elif name=='key':  add(keyfx(),at,.07,pan=rng.uniform(-.2,.2))
    elif name=='pop':  add(popfx(),at,.15); add(bell(88,.6),at+.05,.035)
    elif name=='whoosh': add(whoosh(),at-.35,.10)
    elif name=='success':
        for k,n in enumerate((79,84,88)): add(bell(n),at+k*.11,.06)
    elif name=='impact':
        add(swell(),at-.9,.12); add(bloom(),at,.22); add(bell(91,1.8),at+.05,.03)
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
m=np.tanh(m*1.1)/np.tanh(1.1); m/=np.abs(m).max()/0.8
w=wave.open(OUT,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((m*32767).astype('<i2').tobytes()); w.close()
print('audio ok', OUT)
