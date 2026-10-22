import sys, os, base64, time, subprocess, threading, http.server, functools, shutil
from playwright.sync_api import sync_playwright
V=os.path.abspath(sys.argv[1]); OUT=os.path.abspath(sys.argv[2]); FR=os.path.join(V,'..','frames'); shutil.rmtree(FR,ignore_errors=True); os.makedirs(FR)
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(http.server.SimpleHTTPRequestHandler,directory=V))
threading.Thread(target=srv.serve_forever,daemon=True).start()
frames=[]
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1080,'height':1920},device_scale_factor=1); pg=ctx.new_page()
    errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
    cdp=ctx.new_cdp_session(pg)
    def on_frame(ev):
        frames.append((ev['metadata']['timestamp'], ev['data'])); cdp.send('Page.screencastFrameAck',{'sessionId':ev['sessionId']})
    cdp.on('Page.screencastFrame',on_frame)
    cdp.send('Page.startScreencast',{'format':'jpeg','quality':92,'maxWidth':1080,'maxHeight':1920,'everyNthFrame':1})
    pg.goto('http://127.0.0.1:8765/stage.html')
    pg.wait_for_function('window.__done===true',timeout=60000)
    start=pg.evaluate('window.__start')/1000; err=pg.evaluate('window.__err||null')
    import json; json.dump(pg.evaluate('window.__ev'),open(OUT+'.events.json','w'))
    cdp.send('Page.stopScreencast'); b.close()
print('frames',len(frames),'err',err,'pageerrors',errs[:3])
fr=[(t,d) for t,d in frames if t>=start-0.05]
# keep last frame before start too
before=[(t,d) for t,d in frames if t<start-0.05]
if before: fr=[(start,before[-1][1])]+fr
lst=open(os.path.join(FR,'list.txt'),'w')
for i,(t,d) in enumerate(fr):
    fn=os.path.join(FR,f'{i:05d}.jpg'); open(fn,'wb').write(base64.b64decode(d))
    nxt=fr[i+1][0] if i+1<len(fr) else start+15.0
    dur=max(0.001,min(nxt,start+15.0)-max(t,start))
    if t>=start+15.0: break
    lst.write(f"file '{fn}'\nduration {dur:.4f}\n")
lst.write(f"file '{fn}'\n"); lst.close()
import imageio_ffmpeg
ff=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff,'-y','-loglevel','error','-f','concat','-safe','0','-i',os.path.join(FR,'list.txt'),'-vf','fps=30,format=yuv420p','-t','15','-c:v','libx264','-preset','slow','-crf','18','-movflags','+faststart',OUT],check=True)
print('wrote',OUT)
