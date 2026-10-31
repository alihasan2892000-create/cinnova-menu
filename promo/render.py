# تسجيل إطار بإطار بوقت افتراضي (60fps): حركة ناعمة ثابتة مهما كان الجهاز بطيء
import sys, os, json, shutil, subprocess, threading, http.server, functools
from playwright.sync_api import sync_playwright
V=os.path.abspath(sys.argv[1]); OUT=os.path.abspath(sys.argv[2]); FPS=int(sys.argv[3]) if len(sys.argv)>3 else 60; DSF=int(sys.argv[4]) if len(sys.argv)>4 else 1; DUR=float(os.environ.get("DUR","15"))
FR=os.path.join(os.path.dirname(OUT),'frames60'); shutil.rmtree(FR,ignore_errors=True); os.makedirs(FR)
H=functools.partial(http.server.SimpleHTTPRequestHandler,directory=V); H.log_message=lambda *a:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8767),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1080,'height':1920},device_scale_factor=DSF); pg=ctx.new_page()
    errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.clock.install()
    pg.goto('http://127.0.0.1:8767/stage.html')
    pg.wait_for_function('window.__ready===true',timeout=60000); pg.wait_for_timeout(1500)
    import datetime; now=pg.evaluate('Date.now()'); pg.clock.pause_at(datetime.datetime.fromtimestamp((now+50)/1000,datetime.timezone.utc))  # رقم مجرد بينفهم ثواني، فلازم datetime
    pg.evaluate('window.__go=true'); pg.clock.run_for(40)   # أول خطوة بتسجّل __start
    import imageio_ffmpeg
    enc=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','image2pipe','-framerate',str(FPS),'-c:v','png','-i','-',
        '-vf','format=yuv420p','-c:v','libx264','-preset','slow','-crf','12' if DSF>1 else '16','-profile:v','high','-tune','animation','-movflags','+faststart',OUT],stdin=subprocess.PIPE)
    n=int(DUR*FPS); done=0
    for i in range(n):
        if i: pg.clock.run_for(round(i*1000/FPS)-round((i-1)*1000/FPS))
        pg.evaluate('window.__vsync()')
        enc.stdin.write(pg.screenshot(type='png'))
        if i%120==0: print('frame',i,flush=True)
    enc.stdin.close(); enc.wait()
    ev=pg.evaluate('window.__ev'); err=pg.evaluate('window.__err||null'); b.close()
json.dump(ev,open(OUT+'.events.json','w'))
print('frames',n,'err',err,'pageerrors',errs[:3])
print('wrote',OUT)
