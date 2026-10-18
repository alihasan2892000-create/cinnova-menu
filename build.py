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
out.write_text(html, encoding="utf-8")
(ROOT / "public").mkdir(exist_ok=True)
(ROOT / "public" / "index.html").write_text(html, encoding="utf-8")   # published copy (Cloudflare)
# product photos: images/*.webp -> public/images/
if (ROOT / "public" / "images").exists(): shutil.rmtree(ROOT / "public" / "images")
shutil.copytree(ROOT / "images", ROOT / "public" / "images")
print(f"built {out.name} ({len(html)//1024} KB)")
