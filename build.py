"""Build the single-file menu: src/menu.html + assets/* -> cinnova-menu.html (+ public/index.html, deployed by Cloudflare)
Usage:  python build.py
"""
import base64, re, pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parent
A = ROOT / "assets"

def svguri(name):
    s = (A / name).read_text(encoding="utf-8")
    s = re.sub(r"(\d+\.\d{2})\d+", r"\1", s)          # trim float precision
    s = re.sub(r"\s+", " ", s).replace("> <", "><")
    return "data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode()

tile = "data:image/webp;base64," + base64.b64encode((A / "tile.webp").read_bytes()).decode()
html = (ROOT / "src" / "menu.html").read_text(encoding="utf-8")
html = (html.replace("__BADGE__", svguri("logo_badge.svg"))
            .replace("__WORD__",  svguri("logo_word.svg"))
            .replace("__TILE__",  tile)
            .replace("__HERO__",  (A / "hero.svg").read_text(encoding="utf-8")))
out = ROOT / "cinnova-menu.html"
# الملف المستقل (برّا public) ما معه مجلد icons: بنضمّن الأيقونة جوّاه وبنشيل رابط الـ manifest
_ico = "data:image/png;base64," + base64.b64encode((A / "icons" / "icon-192.png").read_bytes()).decode()
standalone_html = re.sub(r'<link rel="manifest"[^>]*>\n?', '', html).replace("icons/apple-touch-icon.png", _ico).replace("icons/icon-192.png", _ico)
out.write_text(standalone_html, encoding="utf-8")
(ROOT / "public").mkdir(exist_ok=True)
(ROOT / "public" / "index.html").write_text(html, encoding="utf-8")   # published copy (Cloudflare)
# product photos: images/*.webp -> public/images/
if (ROOT / "public" / "images").exists(): shutil.rmtree(ROOT / "public" / "images")
shutil.copytree(ROOT / "images", ROOT / "public" / "images")
# تطبيق (PWA): الأيقونات + manifest + service worker. اسم الكاش بيتغيّر مع كل build عشان الجوالات تاخذ التحديث
import hashlib, json
if (ROOT / "public" / "icons").exists(): shutil.rmtree(ROOT / "public" / "icons")
shutil.copytree(A / "icons", ROOT / "public" / "icons")
manifest = {"name": "سينوفا | المنيو", "short_name": "سينوفا", "description": "منيو سينوفا للحلويات: تصفّح الأصناف والأسعار، وأرسل طلبك عبر واتساب",
  "lang": "ar", "dir": "rtl", "start_url": "./", "scope": "./", "display": "standalone", "orientation": "portrait",
  "background_color": "#2C1711", "theme_color": "#2C1711",
  "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
(ROOT / "public" / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
ver = hashlib.sha1(html.encode()).hexdigest()[:10]
(ROOT / "public" / "sw.js").write_text(f"""// service worker: الصفحة من النت أولاً (عشان التحديثات توصل)، والصور من الكاش أولاً
const V="cinnova-{ver}", CORE=["./","icons/icon-192.png","icons/icon-512.png","manifest.webmanifest"];
self.addEventListener("install",e=>{{ self.skipWaiting(); e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).catch(()=>{{}})); }});
self.addEventListener("activate",e=>{{ e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim())); }});
self.addEventListener("fetch",e=>{{
  const r=e.request; if(r.method!=="GET") return;
  const u=new URL(r.url);
  if(r.mode==="navigate"){{ e.respondWith(fetch(r).then(res=>{{ const cp=res.clone(); caches.open(V).then(c=>c.put("./",cp)); return res; }}).catch(()=>caches.match("./").then(m=>m||caches.match(r)))); return; }}
  if(u.origin===location.origin || /fonts\\.(googleapis|gstatic)\\.com$/.test(u.hostname)){{
    e.respondWith(caches.match(r).then(m=>{{ const net=fetch(r).then(res=>{{ if(res.ok||res.type==="opaque"){{ const cp=res.clone(); caches.open(V).then(c=>c.put(r,cp)); }} return res; }}).catch(()=>m); return m||net; }}));
  }}
}});
""", encoding="utf-8")

# صفحة لكل تصميم بالمعرض (public/d/gNN.html) فيها og:image، عشان واتساب يعرض صورة التصميم داخل رسالة الطلب
SITE = "https://cinnova-menu.cinnova.workers.dev"
names = re.findall(r'"([^"]+)"', html[html.index("const GALLERY = ["):html.index("].map((name,i)")])
from PIL import Image
D = ROOT / "public" / "d"; D.mkdir(exist_ok=True)
OG = ROOT / "public" / "images" / "cakes" / "og"; OG.mkdir(parents=True, exist_ok=True)
for i, name in enumerate(names, 1):
    n = f"{i:02d}"
    Image.open(ROOT / "images" / "cakes" / f"g{n}.webp").convert("RGB").resize((640, 800)).save(OG / f"g{n}.jpg", quality=80)
    img = f"{SITE}/images/cakes/og/g{n}.jpg"
    (D / f"g{n}.html").write_text(f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · سينوفا</title>
<meta property="og:type" content="website"><meta property="og:site_name" content="Cinnova sweets">
<meta property="og:title" content="التصميم المطلوب: {name} (رقم {i})"><meta property="og:description" content="من معرض أعمال سينوفا للكيك">
<meta property="og:image" content="{img}"><meta property="og:image:type" content="image/jpeg"><meta property="og:image:width" content="640"><meta property="og:image:height" content="800">
<meta name="twitter:card" content="summary_large_image">
<style>body{{margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;background:#2C1711;color:#F3D275;font-family:system-ui,sans-serif;padding:20px;box-sizing:border-box}}img{{width:min(92vw,480px);border-radius:20px}}a{{color:#2C1711;background:#F3D275;padding:10px 20px;border-radius:12px;text-decoration:none;font-weight:700}}</style></head>
<body><img src="../images/cakes/g{n}.webp" alt="{name}"><h1 style="margin:0;font-size:20px">{name} (رقم {i})</h1><a href="../#/c/gallery">معرض أعمالنا</a></body></html>""", encoding="utf-8")
print(f"built {out.name} ({len(html)//1024} KB), {len(names)} share pages")
