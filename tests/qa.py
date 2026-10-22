"""Full QA of the menu. Run after every change:  python tests/qa.py   (needs: pip install playwright && playwright install chromium)"""
import sys, json, urllib.parse, re, pathlib, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
MENU = ROOT / "cinnova-menu.html"
S = tempfile.mkdtemp(prefix="cinnova-qa-"); pathlib.Path(S, "shots").mkdir()
from playwright.sync_api import sync_playwright
F=MENU.as_uri()
R=[]  # (name, ok, detail)
def chk(name, ok, detail=""): R.append((name, bool(ok), detail))

with sync_playwright() as p:
    b=p.chromium.launch()
    def newctx(w=390,h=844,storage=True):
        ctx=b.new_context(viewport={'width':w,'height':h},device_scale_factor=2,is_mobile=True,has_touch=True)
        ctx.route('**/fonts.g*/**',lambda r:r.abort()); ctx.route('https://wa.me/**',lambda r:r.fulfill(body='ok'))
        return ctx
    ctx=newctx(); pg=ctx.new_page(); errs=[]; urls=[]
    pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' and 'ERR_FAILED' not in m.text else None)
    ctx.on('page',lambda np: urls.append(urllib.parse.unquote(np.url)))
    pg.goto(F); pg.wait_for_timeout(900)
    chk('splash visible at start', pg.locator('#splash').is_visible())
    pg.wait_for_timeout(2400)
    chk('splash gone after ~2.3s', pg.locator('#splash').count()==0)
    chk('home view active', pg.evaluate('document.querySelector("#view-home").classList.contains("active")'))
    chk('hero logo rendered (svg)', pg.locator('#hero-logo svg').count()==1)
    chk('header/foot logos loaded', pg.evaluate('[...document.querySelectorAll("[data-logo]")].every(i=>i.complete&&i.naturalWidth>0)'))
    # data integrity
    data=pg.evaluate('''()=>({cats:CATS.map(c=>c.id), items:ITEMS.map(i=>({id:i.id,cat:i.cat,sub:i.sub,price:i.price,sizes:i.sizes,f:!!i.featured}))})''')
    ids=[i['id'] for i in data['items']]
    chk('no duplicate item ids', len(ids)==len(set(ids)), str([x for x in ids if ids.count(x)>1]))
    bad=[i['id'] for i in data['items'] if i['cat'] not in data['cats']]
    chk('every item has valid category', not bad, str(bad))
    noprice=[i['id'] for i in data['items'] if not i['sizes'] and (i['price'] is None or (isinstance(i['price'],dict) and not i['price']))]
    chk('every item has a price', not noprice, str(noprice))
    # categories grid
    cats=[c for c in data['cats']]
    chk('all category cards on home', pg.locator('.cats [data-a="go"]').count()==len(cats), f"{pg.locator('.cats [data-a=go]').count()} vs {len(cats)}")
    chk('no featured slider on home', pg.locator('#rail').count()==0 and pg.locator('#view-home .feat').count()==0)
    chk('categories come right after the hero', pg.evaluate('document.querySelector(".hero").nextElementSibling.contains(document.querySelector("#cats"))'))
    # visit each category
    for c in cats:
        pg.evaluate(f'go("{c}")'); pg.wait_for_timeout(250)
        exp=sum(1 for i in data['items'] if (i['f'] if c=='featured' else i['cat']==c))
        n=pg.locator('#view-cat .item').count()
        chk(f'category "{c}" shows {exp} items', n==exp and exp>0, f'got {n}')
        empty=pg.evaluate('[...document.querySelectorAll("#view-cat .item")].filter(e=>!e.querySelector(".price b")||e.querySelector(".price b").textContent.trim()===""||/NaN|undefined/.test(e.textContent)).length')
        chk(f'category "{c}" no NaN/undefined', empty==0, str(empty))
    # product photos: every img path exists, and a visible one actually loads
    imgs=pg.evaluate('ITEMS.flatMap(i=>[i.img,...Object.values(i.flavorImgs||{}),...Object.values(i.sizeImgs||{})]).filter(Boolean)')
    missing=[x for x in imgs if not (ROOT/x).exists()]
    chk('all item photos exist on disk', imgs and not missing, str(missing[:5]))
    pg.evaluate('go("sharqi")'); pg.wait_for_timeout(800)
    chk('item photo renders', pg.evaluate('(i=>i&&i.complete&&i.naturalWidth>0)(document.querySelector("#view-cat .thumb img"))'))
    # tap photo -> enlarged view; back button / tap closes it and stays on the category
    pg.locator('#view-cat [data-card="s4"] .thumb img').click(); pg.wait_for_timeout(450)
    chk('photo opens enlarged', pg.evaluate('document.querySelector("#lb").classList.contains("on")') and pg.locator('#lb-img').get_attribute('src')=='images/s4.webp' and pg.locator('#lb-name').inner_text()=='بقلاوة لوز')
    pg.go_back(); pg.wait_for_timeout(450)
    chk('phone back closes photo, stays in category', not pg.evaluate('document.querySelector("#lb").classList.contains("on")') and pg.evaluate('document.querySelector("#view-cat").classList.contains("active")'))
    pg.locator('#view-cat [data-card="s4"] .thumb img').click(); pg.wait_for_timeout(400); pg.locator('#lb-x').click(); pg.wait_for_timeout(450)
    chk('X closes photo, stays in category', not pg.evaluate('document.querySelector("#lb").classList.contains("on")') and pg.evaluate('document.querySelector("#view-cat").classList.contains("active")') and pg.evaluate('document.body.style.overflow')=='')
    # tabs + back
    pg.evaluate('go("sharqi")'); pg.wait_for_timeout(300)
    pg.locator('#tabs [data-c="nuts"]').click(); pg.wait_for_timeout(400)
    chk('tab switch to nuts', pg.locator('#cat-head h1').inner_text()=='مكسرات')
    pg.locator('#view-cat [data-a="home"]').click(); pg.wait_for_timeout(600)
    chk('back button returns home', pg.evaluate('document.querySelector("#view-home").classList.contains("active")'))
    pg.locator('.cats [data-c="petit"]').click(); pg.wait_for_timeout(400)
    pg.go_back(); pg.wait_for_timeout(500)
    chk('phone back returns home', pg.evaluate('document.querySelector("#view-home").classList.contains("active")'))
    # add from a category, badge on home
    pg.evaluate('go("featured")'); pg.wait_for_timeout(300)
    pg.locator('#view-cat [data-card="f2"] [data-a="add"]').click(); pg.wait_for_timeout(900)
    chk('add from featured category', pg.evaluate('cartCount()')==1)
    pg.evaluate('goHome()'); pg.wait_for_timeout(500)
    chk('cart badge shows 1', pg.locator('#view-home .badge').inner_text()=='1')
    # every item add in every category, unit switching
    pg.evaluate('cart={};updateCartUI()')
    fails=[]
    for it in data['items']:
        pg.evaluate(f'go("{it["cat"]}")'); pg.wait_for_timeout(120)
        card=pg.locator(f'#view-cat [data-card="{it["id"]}"]')
        units=pg.evaluate(f'unitsOf(byId["{it["id"]}"])')
        for u in units:
            if len(units)>1: card.locator(f'[data-u="{u}"]').click(); pg.wait_for_timeout(60)
            shown=card.locator('.price b').inner_text()
            exp=pg.evaluate(f'fmt(unitPrice(byId["{it["id"]}"],"{u}"))')
            if shown!=exp: fails.append(f'{it["id"]}/{u} price {shown}!={exp}')
            card.locator('[data-a="add"]').click(); pg.wait_for_timeout(60)
            q=pg.evaluate(f'cart[keyOf(byId["{it["id"]}"],"{u}")]||0')
            if q!=1: fails.append(f'{it["id"]}/{u} add->{q}')
    chk('every item × every unit: price correct + add works', not fails, '; '.join(fails[:6]))
    total_exp=pg.evaluate('ITEMS.reduce((s,i)=>s+unitsOf(i).reduce((t,u)=>t+unitPrice(i,u),0),0)')
    chk('cart total = sum of all', abs(pg.evaluate('cartTotal()')-total_exp)<1e-6, f"{pg.evaluate('cartTotal()')} vs {total_exp}")
    # flavors: pick a flavor, add, separate cart lines per flavor, WA text
    pg.evaluate("cart={};updateCartUI();go('featured')"); pg.wait_for_timeout(300)
    chk('crepe note with WA link', 'كريب سبيشل' in pg.locator('#view-cat .note-card').inner_text() and pg.locator('#view-cat .note-card').get_attribute('href').startswith('https://wa.me/972594870202?text='))
    fc=pg.locator('#view-cat [data-card="f3"]')
    chk('cheesecake shows 4 flavors', fc.locator('.flv button').count()==4)
    fc.locator('[data-f="نوتيلا"]').click(); pg.wait_for_timeout(100)
    chk('flavor switch changes photo', fc.locator('.thumb img').get_attribute('src')=='images/f3_nut.webp')
    fc.locator('[data-f="لوتس"]').click(); pg.wait_for_timeout(100)
    bc=pg.locator('#view-cat [data-card="f2"]'); bc.locator('[data-u="l"]').click(); pg.wait_for_timeout(100)
    chk('size switch changes photo', bc.locator('.thumb img').get_attribute('src')=='images/f2_l.webp')
    bc.locator('[data-u="s"]').click(); pg.wait_for_timeout(100)
    chk('flavor without own photo falls back to item photo', fc.locator('.thumb img').get_attribute('src')=='images/f3.webp')
    fc.locator('[data-f="لوتس"]').click(); fc.locator('[data-a="add"]').click(); pg.wait_for_timeout(100)
    fc.locator('[data-f="بيستاشيو"]').click(); pg.wait_for_timeout(100)
    chk('flavor switch shows add again', fc.locator('[data-a="add"]').count()==1)
    fc.locator('[data-a="add"]').click(); fc.locator('[data-a="inc"]').click(); pg.wait_for_timeout(100)
    chk('flavor cart keys', pg.evaluate('cart["f3|piece|لوتس"]')==1 and pg.evaluate('cart["f3|piece|بيستاشيو"]')==2)
    m=pg.locator('#view-cat [data-card="f1"]'); m.locator('[data-f="لوتس"]').click(); m.locator('[data-u="t"]').click(); m.locator('[data-a="add"]').click(); pg.wait_for_timeout(100)
    chk('mix: flavor+size key', pg.evaluate('cart["f1|t|لوتس"]')==1)
    msg2=pg.evaluate('(form.name="ت",form.mode="pickup",form.time="2030-01-01T10:00",buildMessage())')
    for s2 in ['تشيز كيك بنكهة لوتس — 1 قطعة × 10 = 10 ₪','تشيز كيك بنكهة بيستاشيو — 2 قطعة × 10 = 20 ₪','مكس سينوفا بنكهة لوتس (مثلث) — 1 × 15 = 15 ₪']:
        chk(f'WA flavor line "{s2}"', s2 in msg2, msg2[:200])
    pg.evaluate("cart={};updateCartUI();form={name:'',mode:'',time:'',address:'',notes:''};goHome()"); pg.wait_for_timeout(500)
    # inc/dec/remove in card
    pg.evaluate("cart={};for(const k in unitPick) delete unitPick[k];updateCartUI();go(\"sharqi\")"); pg.wait_for_timeout(300)
    c=pg.locator('#view-cat [data-card="s1"]')
    c.locator('[data-a="add"]').click(); c.locator('[data-a="inc"]').click(); c.locator('[data-a="inc"]').click(); pg.wait_for_timeout(100)
    chk('stepper + to 3', pg.evaluate('cart["s1|kg"]')==3)
    c.locator('[data-a="dec"]').click(); c.locator('[data-a="dec"]').click(); c.locator('[data-a="dec"]').click(); pg.wait_for_timeout(100)
    chk('stepper − removes at 0', pg.evaluate('"s1|kg" in cart')==False and c.locator('[data-a="add"]').count()==1)
    chk('cart bar hidden when empty', not pg.evaluate('document.querySelector("#cartbar").classList.contains("on")'))
    # cart sheet
    c.locator('[data-a="add"]').click(); pg.wait_for_timeout(800)
    chk('cart bar shows when has items', pg.evaluate('document.querySelector("#cartbar").classList.contains("on")'))
    pg.locator('#cartbar button').click(); pg.wait_for_timeout(600)
    chk('cart sheet opens', pg.evaluate('document.querySelector("#sheet").classList.contains("on")'))
    pg.locator('[data-a="cinc"]').first.click(); pg.wait_for_timeout(150)
    chk('cart + in sheet', pg.evaluate('cart["s1|kg"]')==2)
    pg.locator('[data-a="cdec"]').first.click(); pg.locator('[data-a="cdec"]').first.click(); pg.wait_for_timeout(200)
    chk('cart remove last -> empty state', pg.locator('.empty').count()==1)
    pg.locator('#sheet [data-a="close"]').last.click(); pg.wait_for_timeout(500)
    chk('sheet closes', not pg.evaluate('document.querySelector("#sheet").classList.contains("on")'))
    chk('body scroll unlocked', pg.evaluate('document.body.style.overflow')=='')
    # checkout validation
    pg.evaluate('cart={"s1|uqiya":2,"ks1|l":1,"j4|uqiya":3};updateCartUI();openSheet("checkout")'); pg.wait_for_timeout(500)
    pg.locator('[data-a="send"]').click(); pg.wait_for_timeout(300)
    bads=pg.evaluate('[...document.querySelectorAll(".field.bad")].map(e=>e.id)')
    chk('checkout blocks empty form (name, mode, time)', set(['f-name','f-mode','f-time'])<=set(bads) and len(urls)==0, str(bads))
    pg.fill('#i-name','تجربة'); pg.locator('[data-m="delivery"]').click(); pg.fill('#i-time','2026-10-20T16:00'); pg.wait_for_timeout(300)
    chk('address field appears for delivery', pg.evaluate('document.querySelector("#addr-wrap").classList.contains("open")'))
    pg.locator('[data-a="send"]').click(); pg.wait_for_timeout(300)
    chk('delivery requires address', 'f-addr' in pg.evaluate('[...document.querySelectorAll(".field.bad")].map(e=>e.id)') and len(urls)==0)
    pg.fill('#i-addr','دير البلح'); pg.fill('#i-notes','بدون مكسرات')
    pg.locator('[data-a="send"]').click(); pg.wait_for_timeout(1000)
    chk('WhatsApp opens on valid order', len(urls)==1)
    msg=urls[-1] if urls else ''
    chk('WA number correct', msg.startswith('https://wa.me/972594870202?text='))
    for s in ['أساور — 2 وقية × 12 = 24 ₪','كيك نوتيلا (كبير · 12 قطعة) — 1 × 120 = 120 ₪','جلي تركي — 3 وقية × 8 = 24 ₪','المجموع: 168 ₪','الاسم: تجربة','توصيل','العنوان: دير البلح','ملاحظات: بدون مكسرات']:
        chk(f'WA msg contains "{s}"', s in msg)
    chk('success screen', pg.locator('.success').count()==1)
    chk('cart cleared after send', pg.evaluate('cartCount()')==0)
    pg.locator('[data-a="resend"]').click(); pg.wait_for_timeout(700)
    chk('resend opens WA again', len(urls)==2 and urls[-1]==urls[-2])
    pg.locator('#sheet [data-a="close"]').first.click(); pg.wait_for_timeout(400)
    # pickup: no address in msg
    pg.evaluate('cart={"c1|uqiya":1};updateCartUI();form={name:"",mode:"",time:"",address:"",notes:""};openSheet("checkout")'); pg.wait_for_timeout(400)
    pg.fill('#i-name','ب'); pg.locator('[data-m="pickup"]').click(); pg.fill('#i-time','2026-10-20T16:00'); pg.locator('[data-a="send"]').click(); pg.wait_for_timeout(800)
    chk('pickup order: no address line', 'العنوان' not in urls[-1] and 'استلام من المحل' in urls[-1])
    pg.locator('#sheet [data-a="close"]').first.click(); pg.wait_for_timeout(400)
    # slab cake needs booking a day ahead
    lt='h=>{const d=new Date(Date.now()+h*3600e3);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16)}'
    pg.evaluate('cart={"kb1|s":1};updateCartUI();form={name:"",mode:"",time:"",address:"",notes:""};openSheet("checkout")'); pg.wait_for_timeout(400)
    chk('slab: 24h hint shown', 'قبل 24 ساعة' in pg.locator('#f-time').inner_text())
    pg.fill('#i-name','ب'); pg.locator('[data-m="pickup"]').click(); pg.fill('#i-time',pg.evaluate(f'({lt})(3)'))
    n0=len(urls); pg.locator('[data-a="send"]').click(); pg.wait_for_timeout(300)
    chk('slab: rejects time < 24h', len(urls)==n0 and pg.locator('#f-time.bad').count()==1)
    pg.fill('#i-time',pg.evaluate(f'({lt})(30)')); pg.locator('[data-a="send"]').click(); pg.wait_for_timeout(800)
    chk('slab: order sent after 24h', len(urls)==n0+1 and 'بلاطة سبيشل (نصف بلاطة · 25 - 30 قطعة) — 1 × 150 = 150 ₪' in urls[-1])
    pg.locator('#sheet [data-a="close"]').first.click(); pg.wait_for_timeout(400)
    # cake builder
    pg.evaluate('go("cake")'); pg.wait_for_timeout(500)
    chk('cake subnav 4 buttons', pg.locator('.subnav button').count()==4)
    chk('slab size labels', pg.locator('[data-card="kb1"] .seg button').all_inner_texts()==['نصف بلاطة','بلاطة'])
    pg.locator('[data-card="kb1"] [data-u="l"]').click(); pg.wait_for_timeout(150)
    chk('slab large price/pieces', '300' in pg.locator('#view-cat [data-card="kb1"] [data-price]').inner_text() and '60 - 70 قطعة' in pg.locator('#view-cat [data-card="kb1"] [data-price]').inner_text())
    chk('cake slices sold by piece', pg.locator('[data-card="kc2"] .unit-chip').inner_text()=='بالقطعة')
    chk('triangle shows 3 flavors', pg.locator('#view-cat [data-card="kc2"] .flv button').all_inner_texts()==['نوتيلا','بيستاشيو','لوتس'])
    chk('sharqi items also in featured', pg.evaluate('["s12","s22","s23"].every(id=>itemsIn("featured").includes(byId[id]) && byId[id].cat==="sharqi")'))
    chk('flavor names read naturally', pg.evaluate('[withFlavor("كرواسون بيضاوي","بالجبنة الصفراء",byId.m10), withFlavor("معجنات باللحوم","كفتة عجل",byId.m11), withFlavor("كيت كات","بلوبيري",byId.m8)]')==['كرواسون بيضاوي بالجبنة الصفراء','معجنات باللحوم — كفتة عجل','كيت كات بنكهة بلوبيري'])
    chk('layer cake moved to cake slices', pg.evaluate('byId.f5.cat==="cake" && byId.f5.sub==="slice" && !byId.f5.featured'))
    chk('super special: small 65 (nutella 60), large 12 pcs', pg.evaluate('byId.ks1.sizes.s.price===60 && ["ks2","ks3","ks4","ks5","ks6","ks7"].every(k=>byId[k].sizes.s.price===65) && ITEMS.filter(i=>i.sub==="super"||i.sub==="special").every(i=>i.sizes.s.pieces===6&&i.sizes.l.pieces===12)'))
    chk('custom cake sizes: slabs, no tiers', pg.evaluate('JSON.stringify(CAKE.size.map(x=>x.name))')=='["صغيرة","وسط","نصف بلاطة","بلاطة"]')
    chk('super special slab prices', pg.evaluate('[unitPrice(byId.kb2,"s"),unitPrice(byId.kb2,"l")]')==[170,340])
    chk('cake sub headers', pg.locator('.subhead').count()==4)
    pg.locator('.cake-banner').click(); pg.wait_for_timeout(500)
    pg.locator('[data-a="cake-step"][data-s="2"]').click(); pg.wait_for_timeout(200)
    chk('cake step1 validation', pg.locator('.field.bad').count()>=3)
    for k,v in [('occasion','bday'),('size','m'),('shape','num')]: pg.locator(f'[data-k="{k}"][data-v="{v}"]').click()
    pg.locator('[data-a="cake-step"][data-s="2"]').click(); pg.wait_for_timeout(200)
    chk('cake requires number when shape=num', pg.locator('#f-num.bad').count()==1)
    chk('cake bar hidden at top', not pg.evaluate('document.querySelector("#cake-bar").classList.contains("show")'))
    pg.evaluate('document.querySelector("#sheet .sheet-body").scrollTop=10000'); pg.wait_for_timeout(400)
    chk('cake bar shows on scroll + summary', pg.evaluate('document.querySelector("#cake-bar").classList.contains("show")') and 'رقم أو حرف' in pg.locator('#cake-bar p').inner_text())
    pg.fill('#i-num','30'); pg.locator('[data-a="cake-step"][data-s="2"]').click(); pg.wait_for_timeout(300)
    chk('cake goes to step 2', pg.locator('#f-flavor').count()==1)
    pg.locator('[data-a="cake-step"][data-s="3"]').click(); pg.wait_for_timeout(200)
    chk('cake step2 validation', pg.locator('.field.bad').count()>=4)
    for k,v in [('flavor','lotus'),('filling','cream'),('deco','fondant'),('color','gold')]: pg.locator(f'[data-k="{k}"][data-v="{v}"]').click()
    pg.fill('#i-text','مبروك'); pg.locator('[data-a="cake-step"][data-s="1"]').click(); pg.wait_for_timeout(200)
    chk('cake back to step1 keeps choices', pg.locator('[data-k="size"][data-v="m"].on').count()==1 and pg.input_value('#i-num')=='30')
    pg.locator('[data-a="cake-step"][data-s="2"]').click(); pg.wait_for_timeout(200)
    chk('cake step2 keeps text', pg.input_value('#i-text')=='مبروك')
    pg.locator('[data-a="cake-step"][data-s="3"]').click(); pg.wait_for_timeout(200)
    pg.fill('#i-name','ك'); pg.locator('[data-a="cake-mode"][data-m="pickup"]').click()
    from datetime import datetime, timedelta
    soon=(datetime.now()+timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M')
    pg.fill('#i-time',soon); n0=len(urls); pg.locator('[data-a="cake-send"]').click(); pg.wait_for_timeout(300)
    chk('cake rejects time < 24h', len(urls)==n0 and pg.locator('#f-time.bad').count()==1)
    later=(datetime.now()+timedelta(days=3)).strftime('%Y-%m-%dT%H:%M')
    pg.fill('#i-time',later); pg.locator('[data-a="cake-send"]').click(); pg.wait_for_timeout(800)
    cm=urls[-1] if len(urls)>n0 else ''
    chk('cake WA message sent', bool(cm))
    for s in ['كيكة خاصة','رقم أو حرف — 30','لوتس','فوندان','ذهبي','الكتابة: مبروك','بانتظار تأكيد السعر']:
        chk(f'cake msg has "{s}"', s in cm)
    chk('cake order did not touch cart', pg.evaluate('cartCount()')==0)
    pg.locator('#sheet [data-a="close"]').first.click(); pg.wait_for_timeout(300)
    # links
    chk('header WA link', pg.evaluate('document.querySelector("#wa-top").href')=='https://wa.me/972594870202')
    chk('call link', pg.evaluate('document.querySelector("#call-btn").href')=='tel:+972594870202')
    # persistence
    pg.evaluate('go("nuts")'); pg.wait_for_timeout(200); pg.locator('#view-cat [data-card="n1"] [data-a="add"]').click(); pg.wait_for_timeout(300)
    pg.reload(); pg.wait_for_timeout(1500)
    chk('cart persists after reload', pg.evaluate('cartCount()')==1)
    chk('splash not repeated in same session', pg.locator('#splash').count()==0)
    chk('reload on #/c/nuts opens nuts', pg.locator('#cat-head h1').inner_text()=='مكسرات' if pg.evaluate('document.querySelector("#view-cat").classList.contains("active")') else False)
    chk('no JS errors (main run)', not errs, '; '.join(errs[:3]))
    ctx.close()

    # small phone width overflow
    for w in [320,360,414]:
        ctx=newctx(w,740); pg=ctx.new_page(); e2=[]; pg.on('pageerror',lambda e: e2.append(str(e)))
        pg.goto(F); pg.wait_for_timeout(3000)
        over=[]
        for c in cats:
            pg.evaluate(f'go("{c}")'); pg.wait_for_timeout(150)
            if pg.evaluate('document.documentElement.scrollWidth')>w: over.append(c)
        pg.evaluate('openSheet("cake1")'); pg.wait_for_timeout(300)
        if pg.evaluate('document.documentElement.scrollWidth')>w: over.append('cake-sheet')
        pg.evaluate('closeSheet();goHome()'); pg.wait_for_timeout(300)
        if pg.evaluate('document.documentElement.scrollWidth')>w: over.append('home')
        # card overflow inside
        clip=0
        for cc in ['featured','cake','sharqi','nuts','jelly','party','coffee','petit','pastry']:
            pg.evaluate(f'go("{cc}")'); pg.wait_for_timeout(120)
            clip+=pg.evaluate('[...document.querySelectorAll(".item .row")].filter(r=>r.scrollWidth>r.clientWidth+1).length')
            pg.evaluate('document.querySelectorAll("#view-cat [data-a=add]").forEach(b=>b.click())'); pg.wait_for_timeout(120)
            clip+=pg.evaluate('[...document.querySelectorAll(".item .row")].filter(r=>r.scrollWidth>r.clientWidth+1).length')
        chk(f'width {w}px: no horizontal overflow', not over, str(over))
        chk(f'width {w}px: item rows fit', clip==0, f'{clip} rows overflow')
        if w==320: pg.screenshot(path=S+'/shots/qa320.png')
        chk(f'width {w}px: no errors', not e2, str(e2[:2])); ctx.close()

    # sandboxed preview (no storage, no history)
    html=open(MENU,encoding='utf-8').read()
    open(S+'/frame.html','w').write('<body style="margin:0"><iframe id="f" sandbox="allow-scripts allow-popups" style="border:0;width:390px;height:844px"></iframe><script>document.getElementById("f").srcdoc='+json.dumps(html).replace("</","<\\/")+'</script></body>')
    ctx=newctx(); pg=ctx.new_page(); e3=[]; pg.on('pageerror',lambda e: e3.append(str(e)))
    pg.goto('file://'+S+'/frame.html'); pg.wait_for_timeout(3300); fr=pg.frame_locator('#f')
    fr.locator('.cats [data-c="sharqi"]').click(); pg.wait_for_timeout(400)
    fr.locator('#view-cat [data-card="s1"] [data-a="add"]').click(); pg.wait_for_timeout(900)
    ok=fr.locator('#cb-n').inner_text()=='1'
    fr.locator('#view-cat [data-a="home"]').click(); pg.wait_for_timeout(700)
    chk('sandboxed preview: navigate + add + back work', ok and fr.locator('#view-home.active').count()==1)
    chk('sandboxed preview: no JS errors', not e3, str(e3[:2])); ctx.close()

    # reduced motion
    ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce'); ctx.route('**/fonts.g*/**',lambda r:r.abort())
    pg=ctx.new_page(); pg.goto(F); pg.wait_for_timeout(2600)
    chk('reduced-motion: content visible', pg.evaluate('getComputedStyle(document.querySelector(".hero h1")).opacity')=='1')
    ctx.close(); b.close()

fails=[r for r in R if not r[1]]
for n,ok,d in R: print(('PASS ' if ok else 'FAIL ')+n+(('  -> '+d) if (d and not ok) else ''))
print(f'\n{len(R)-len(fails)}/{len(R)} passed')
