"""Slider (featured rail) touch + mouse test:  python tests/slider.py"""
import sys, json, urllib.parse, re, pathlib, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
MENU = ROOT / "cinnova-menu.html"
S = tempfile.mkdtemp(prefix="cinnova-qa-"); pathlib.Path(S, "shots").mkdir()
import sys, time
from playwright.sync_api import sync_playwright
F=MENU.as_uri()
def swipe(cdp,x0,y0,x1,y1,steps=14,fast=False):
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x0,'y':y0}]})
    for i in range(1,steps+1):
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x0+(x1-x0)*i/steps,'y':y0+(y1-y0)*i/steps}]})
        if not fast: time.sleep(0.012)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
with sync_playwright() as p:
    b=p.chromium.launch(); errs=[]
    # --- touch phone
    ctx=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2); ctx.route('**/fonts.g*/**',lambda r:r.abort()); pg=ctx.new_page()
    pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.goto(F); pg.wait_for_timeout(4200)
    st=lambda: pg.evaluate('[Math.round(document.querySelector("#rail").scrollLeft), railIndex(), [...document.querySelectorAll("#rail-dots button")].findIndex(d=>d.classList.contains("on"))]')
    box=pg.locator('#rail').bounding_box(); cy=box['y']+box['height']*0.4; cdp=ctx.new_cdp_session(pg)
    print('touch start [scrollLeft, idx, activeDot]', st(), 'arrows visible:', pg.locator('.rail-nav').is_visible())
    for i in range(6): swipe(cdp,90,cy,330,cy); pg.wait_for_timeout(900); print(' swipe->',st())
    for i in range(2): swipe(cdp,40,cy,370,cy,fast=True); pg.wait_for_timeout(1100); print(' fling->',st())
    for i in range(5): swipe(cdp,330,cy,90,cy); pg.wait_for_timeout(900); print(' swipe<-',st())
    for k in [3,1,4,0]:
        pg.locator('#rail-dots button').nth(k).click(); pg.wait_for_timeout(1000); print(f' dot {k} ->',st())
    swipe(cdp,90,cy,330,cy); pg.wait_for_timeout(900); print(' swipe after dots ->',st())
    pg.screenshot(path=S+'/shots/rail_touch.png', clip={'x':0,'y':box['y']-60,'width':390,'height':box['height']+100})
    ctx.close()
    # --- desktop mouse
    ctx=b.new_context(viewport={'width':1200,'height':900}); ctx.route('**/fonts.g*/**',lambda r:r.abort()); pg=ctx.new_page()
    pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.goto(F); pg.wait_for_timeout(4200)
    st=lambda: pg.evaluate('[Math.round(document.querySelector("#rail").scrollLeft), railIndex()]')
    box=pg.locator('#rail').bounding_box(); cy=box['y']+box['height']*0.4; x=box['x']
    print('desktop start', st(), 'arrows visible:', pg.locator('.rail-nav').is_visible(), 'prev disabled:', pg.locator('#rail-prev').is_disabled())
    for i in range(5):
        pg.mouse.move(x+80,cy); pg.mouse.down(); pg.mouse.move(x+380,cy,steps=12); pg.mouse.up(); pg.wait_for_timeout(800); print(' drag->',st())
    print(' next disabled at end:', pg.locator('#rail-next').is_disabled())
    for i in range(5):
        if pg.locator('#rail-prev').is_disabled(): break
        pg.locator('#rail-prev').click(); pg.wait_for_timeout(800); print(' prev', st())
    print(' prev disabled at start:', pg.locator('#rail-prev').is_disabled())
    pg.locator('#rail-next').click(); pg.wait_for_timeout(700); print(' next', st())
    # drag must not trigger add; plain click must
    pg.evaluate('cart={};updateCartUI()')
    addb=pg.locator('#rail .feat').nth(1).locator('[data-a="add"]'); bb=addb.bounding_box()
    pg.mouse.move(bb['x']+10,bb['y']+10); pg.mouse.down(); pg.mouse.move(bb['x']+250,bb['y']+10,steps=10); pg.mouse.up(); pg.wait_for_timeout(800)
    print(' cart after drag starting on + :', pg.evaluate('cartCount()'))
    pg.locator('#rail .feat').nth(railIndex:=0).locator('[data-a="add"]').click() if False else None
    vis=pg.evaluate('railIndex()'); pg.locator('#rail .feat').nth(vis).locator('[data-a="add"]').click(); pg.wait_for_timeout(900)
    print(' cart after normal click on + :', pg.evaluate('cartCount()'))
    # tabs drag on desktop
    pg.evaluate('go("sharqi")'); pg.wait_for_timeout(500)
    tb=pg.locator('#tabs').bounding_box(); t0=pg.evaluate('document.querySelector("#tabs").scrollLeft')
    pg.mouse.move(tb['x']+60,tb['y']+20); pg.mouse.down(); pg.mouse.move(tb['x']+300,tb['y']+20,steps=10); pg.mouse.up(); pg.wait_for_timeout(700)
    print(' tabs drag scrollLeft', t0,'->',pg.evaluate('Math.round(document.querySelector("#tabs").scrollLeft)'), 'still on sharqi:', pg.locator('#cat-head h1').inner_text())
    pg.evaluate('goHome()'); pg.wait_for_timeout(700)
    pg.screenshot(path=S+'/shots/rail_desk.png', clip={'x':360,'y':box['y']-60,'width':480,'height':box['height']+100})
    print('errors', errs)
    b.close()
