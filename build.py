#!/usr/bin/env python3
"""
Build the website.

    python build.py             ->  _site/            (what GitHub Pages serves)
    python build.py --preview   ->  _preview/index.html  (single-file preview of every page)

Sources
    content/*.md      pages (Markdown with a small YAML header)
    data/*.yml        site settings, highlights, members, publications
    templates/*.html  page layouts
    assets/           css and images

Images
    Write ![caption](research/foo.jpg) in Markdown; the file lives in assets/img/research/foo.jpg.
    A non-empty caption becomes a figure caption. A missing file shows a labelled placeholder,
    so the page never breaks while images are still being added.
    Highlight images need no setting at all: assets/img/highlights/<id>.jpg (or .png/.webp).
"""

from __future__ import annotations

import argparse
import base64
import os
import hashlib
import html
import mimetypes
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
CONTENT, DATA, TEMPLATES, ASSETS = ROOT / "content", ROOT / "data", ROOT / "templates", ROOT / "assets"
IMG = ASSETS / "img"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")


# --------------------------------------------------------------------------- helpers

def load_yaml(name: str, default=None):
    p = DATA / name
    if not p.exists():
        return default
    return yaml.safe_load(p.read_text(encoding="utf-8")) or default


def split_front(text: str):
    if text.startswith("---\n"):
        _, fm, body = text.split("---\n", 2)
        return yaml.safe_load(fm) or {}, body
    return {}, text


def find_image(name: str | None) -> Path | None:
    """Resolve 'research/foo.jpg' -> assets/img/research/foo.<any ext>, or None."""
    if not name:
        return None
    p = IMG / name
    if p.exists():
        return p
    for ext in IMG_EXT:
        q = p.with_suffix(ext)
        if q.exists():
            return q
    return None


def placeholder_svg(key: str, label: str) -> str:
    """A calm radio-map style placeholder that is obviously not a real picture."""
    h = int(hashlib.sha1(key.encode()).hexdigest(), 16)
    r = lambda n, m: ((h >> n) & 255) / 255 * m
    rot, n = -60 + r(0, 120), 4 + int(r(3, 3))
    cx, cy = 38 + r(5, 24), 40 + r(7, 20)
    rings = "".join(
        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{(14 + r(11, 16)) * k:.1f}" ry="{(8 + r(13, 9)) * k:.1f}" '
        f'transform="rotate({rot:.0f} {cx:.1f} {cy:.1f})" fill="none" stroke="#d98a1f" '
        f'stroke-width="{0.7 + k * 0.5:.2f}" opacity="{0.25 + k * 0.5:.2f}"/>'
        for k in [(n - i) / n for i in range(n)])
    grid = "".join(f'<line x1="0" y1="{i*12}" x2="100" y2="{i*12}"/>' for i in range(7)) + \
           "".join(f'<line x1="{i*12}" y1="0" x2="{i*12}" y2="80"/>' for i in range(9))
    return (f'<span class="ph"><svg viewBox="0 0 100 80" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<g stroke="currentColor" stroke-width=".3" opacity=".12">{grid}</g>{rings}'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.5" fill="#d98a1f"/></svg>'
            f'<span class="slot">{html.escape(label)}</span></span>')


# --------------------------------------------------------------------------- build context

class Builder:
    def __init__(self, preview: bool):
        self.preview = preview
        self.site = load_yaml("site.yml", {})
        self.env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True,
                               trim_blocks=True, lstrip_blocks=True)
        self.md = markdown.Markdown(extensions=["extra", "sane_lists", "toc"],
                                    extension_configs={"toc": {"permalink": False}})
        self.missing_images: set[str] = set()
        self.used_images: set[str] = set()
        # "/repo" when served at https://user.github.io/repo/ before the domain is connected
        self.base = "" if preview else os.environ.get("SITE_BASEURL", self.site.get("baseurl", "")).rstrip("/")

    # ---- urls
    def href(self, url: str) -> str:
        if self.preview and url.startswith("/"):
            slug = url.strip("/") or "home"
            return "#" + slug.split("#")[0].split("/")[0]
        return self.base + url if url.startswith("/") else url

    def asset(self, rel: str) -> str:
        # ?v=<hash> makes browsers fetch the file again whenever it changes
        f = ASSETS / rel
        v = hashlib.sha1(f.read_bytes()).hexdigest()[:8] if f.exists() else ""
        return f"{self.base}/assets/{rel}" + (f"?v={v}" if v else "")

    def image_src(self, name: str) -> str | None:
        p = find_image(name)
        if not p:
            self.missing_images.add(name)
            return None
        rel = p.relative_to(IMG).as_posix()
        self.used_images.add(rel)
        if self.preview:
            return self._preview_uri(p)
        return f"{self.base}/assets/img/{rel}"

    def _preview_uri(self, p: Path) -> str:
        """Single-file preview: embed a downscaled copy (keeps the file small)."""
        cache = self.__dict__.setdefault("_uri_cache", {})
        if p in cache:
            return cache[p]
        if p.suffix.lower() == ".svg":
            uri = "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()
        else:
            try:
                from PIL import Image
                import io
                im = Image.open(p)
                im.thumbnail((1200, 1200))
                if im.mode not in ("RGB", "L"):
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    bg.paste(im, mask=im.convert("RGBA").split()[-1])
                    im = bg
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=72, optimize=True)
                uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
            except Exception:
                mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
                uri = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
        cache[p] = uri
        return uri

    def figure(self, name: str, caption: str = "", link: bool = False, thumb: bool = False) -> Markup:
        src = self.image_src(name)
        if not src:
            return Markup(placeholder_svg(name, f"assets/img/{name}"))
        img = f'<img src="{src}" alt="{html.escape(caption)}" loading="lazy">'
        if thumb:   # fixed-shape frame: whole figure visible, blurred copy fills the rest
            return Markup(f'<span class="thumb" style="--img:url(\'{src}\')">{img}</span>')
        return Markup(img)

    def md_inline(self, text: str) -> Markup:
        out = markdown.markdown(text or "")
        out = re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.S)
        return Markup(self.fix_links(out))

    # ---- markdown post-processing
    def fix_links(self, html_text: str) -> str:
        soup = BeautifulSoup(html_text, "html.parser")
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if h.startswith("http"):
                a["target"], a["rel"] = "_blank", "noopener"
            elif h.startswith("/") and not (self.base and h.startswith(self.base + "/")):
                a["href"] = self.href(h)
        return str(soup)

    def render_markdown(self, body: str) -> str:
        self.md.reset()
        raw = self.md.convert(body)
        soup = BeautifulSoup(raw, "html.parser")

        # images -> real file, figure with caption, or placeholder
        for img in soup.find_all("img"):
            name, caption = img.get("src", ""), img.get("alt", "")
            if name.startswith(("http", "/", "data:")):
                continue
            src = self.image_src(name)
            if src:
                new = soup.new_tag("img", src=src, alt=caption, loading="lazy")
                inner = soup.new_tag("a", href=src if not self.preview else "#", target="_blank")
                inner.append(new)
                node = inner
            else:
                node = BeautifulSoup(placeholder_svg(name, f"assets/img/{name}"), "html.parser")
            fig = soup.new_tag("figure")
            if img.get("class"):            # {: .wide}, {: .logo} ... carried over to the figure
                fig["class"] = list(img.get("class"))
            fig.append(node)
            if caption:
                fc = soup.new_tag("figcaption")
                fc.string = caption
                fig.append(fc)
            parent = img.parent
            if parent.name == "p" and len([c for c in parent.contents if str(c).strip()]) == 1:
                parent.replace_with(fig)
            else:
                img.replace_with(fig)

        # CV rows:  "- 2024-2026 | text"  ->  two columns (works for tight and loose lists)
        for li in soup.find_all("li"):
            target = li.find("p", recursive=False) or li
            first = next((c for c in target.contents if not (isinstance(c, str) and not c.strip())), None)
            if not (isinstance(first, str) and " | " in first):
                continue
            when, rest = first.split(" | ", 1)
            if len(when.strip()) > 24:
                continue
            first.replace_with(rest.lstrip())
            span_t = soup.new_tag("span")
            for c in list(target.contents):
                span_t.append(c.extract())
            span_w = soup.new_tag("span", attrs={"class": "when"})
            span_w.string = when.strip()
            li.clear()
            li["class"] = li.get("class", []) + ["row"]
            li.append(span_w)
            li.append(span_t)

        # <!-- highlights: id1, id2 -->  ->  a row of highlight cards
        from bs4 import Comment
        for c in soup.find_all(string=lambda t: isinstance(t, Comment) and t.strip().startswith("highlights:")):
            ids = [i.strip() for i in c.strip()[len("highlights:"):].split(",") if i.strip()]
            cards, _ = self.highlight_cards(only=ids)
            html_cards = self.env.get_template("_cards.html").render(cards=cards, md_inline=self.md_inline)
            c.replace_with(BeautifulSoup('<div class="related">' + html_cards + "</div>", "html.parser"))

        # <!-- projects -->  ->  project / facility cards from data/projects.yml
        for c in soup.find_all(string=lambda t: isinstance(t, Comment) and t.strip() == "projects"):
            projects = []
            for p in load_yaml("projects.yml", []) or []:
                imgs = p.get("image") or [f"projects/{p['id']}.jpg"]
                imgs = [imgs] if isinstance(imgs, str) else imgs
                name = next((i for i in imgs if find_image(i)), imgs[0])
                projects.append({**p, "figure": self.figure(name, p.get("name", ""), thumb=True)})
            c.replace_with(BeautifulSoup(self.env.get_template("_projects.html").render(projects=projects), "html.parser"))

        return self.fix_links(str(soup))

    # ---- pages
    def pages(self):
        pages = []
        for path in sorted(CONTENT.glob("*.md")):
            fm, body = split_front(path.read_text(encoding="utf-8"))
            slug = path.stem
            fm.setdefault("title", slug.replace("-", " ").title())
            fm["slug"] = slug
            fm["url"] = "/" if slug == "home" else f"/{slug}/"
            pages.append((fm, body))
        for slug, layout, title in [("highlights", "highlights", "Highlights"), ("members", "members", "Members")]:
            if not (CONTENT / f"{slug}.md").exists():
                pages.append(({"slug": slug, "url": f"/{slug}/", "title": title, "layout": layout}, ""))
        return pages

    def highlight_cards(self, limit=None, only=None):
        items = load_yaml("highlights.yml", []) or []
        if only:
            by_id = {h["id"]: h for h in items}
            items = [by_id[i] for i in only if i in by_id]
        cards = []
        for h in items[:limit] if limit else items:
            name = h.get("image") or f"highlights/{h['id']}.jpg"
            cards.append({**h, "figure": self.figure(name, h.get("title", ""), thumb=True)})
        return cards, len(items)

    def pubs_by_year(self):
        pubs = load_yaml("publications.yml", []) or []
        years = {}
        for p in pubs:
            authors = p.get("authors") or []
            short = (authors[0].split(",")[0] + (" et al." if len(authors) > 1 else "")) if authors else ""
            title = html.escape(p.get("title") or "")
            title = re.sub(r"&lt;(/?)(sup|sub|i|b)&gt;", r"<\1\2>", title, flags=re.I)   # keep ADS super/subscripts
            years.setdefault(p.get("year"), []).append({**p, "authors_short": short, "title_html": Markup(title)})
        return sorted(years.items(), key=lambda kv: -(kv[0] or 0))

    def pub_stats(self):
        """Numbers, two charts and short lists for the top of the Publications page."""
        pubs = load_yaml("publications.yml", []) or []
        if not pubs:
            return None

        def is_me(name: str) -> bool:
            n = (name or "").lower()
            return n.startswith("kim, j") and ("young" in n or "j.-y" in n or "j. -y" in n or "j.y" in n)

        def kind(p):
            a = p.get("authors") or []
            if a and is_me(a[0]):
                return "first"
            return "collab" if (p.get("n_authors") or len(a)) > 50 else "team"

        cites = sorted((p.get("citations") or 0 for p in pubs), reverse=True)
        h = sum(1 for i, c in enumerate(cites, 1) if c >= i)
        i10 = sum(1 for c in cites if c >= 10)
        years = sorted({p["year"] for p in pubs if p.get("year")})
        years = list(range(years[0], years[-1] + 1))
        per = {y: {"first": 0, "team": 0, "collab": 0} for y in years}
        cit_year = {y: 0 for y in years}
        for p in pubs:
            if p.get("year") in per:
                per[p["year"]][kind(p)] += 1
                cit_year[p["year"]] += p.get("citations") or 0

        def chart(values_by_year, stacked, label):
            w, hgt = 720, 230
            bw = w / len(years)
            top = max((sum(v.values()) if stacked else v) for v in values_by_year.values()) or 1
            out = []
            for i, y in enumerate(years):
                v = values_by_year[y]
                x = i * bw + bw * 0.18
                base = hgt - 18
                parts = [("first", v["first"]), ("team", v["team"]), ("collab", v["collab"])] if stacked else [("team", v)]
                total = 0
                for cls, n in parts:
                    bh = (hgt - 40) * n / top
                    if n:
                        out.append(f'<rect class="{cls}" x="{x:.1f}" y="{base - bh:.1f}" width="{bw*0.64:.1f}" height="{bh:.1f}"><title>{y}: {n}</title></rect>')
                    base -= bh
                    total += n
                if total:
                    lab = f"{total:,}" if not stacked else str(total)
                    out.append(f'<text class="n" x="{i*bw + bw/2:.1f}" y="{base - 4:.1f}">{lab}</text>')
                if y % 2 == years[-1] % 2 or len(years) <= 12:
                    out.append(f'<text x="{i*bw + bw/2:.1f}" y="{hgt - 4}">{y}</text>')
            return Markup(f'<svg class="pubchart" viewBox="0 0 {w} {hgt}" role="img" aria-label="{label}">{"".join(out)}</svg>')

        def title_html(t):
            t = html.escape(t or "")
            return Markup(re.sub(r"&lt;(/?)(sup|sub|i|b)&gt;", r"<\1\2>", t, flags=re.I))

        top_cited = [{**p, "title_html": title_html(p.get("title"))}
                     for p in sorted(pubs, key=lambda p: -(p.get("citations") or 0))[:5]]
        journals = {}
        for p in pubs:
            j = (p.get("journal") or "").strip()
            if j:
                journals[j] = journals.get(j, 0) + 1
        return {
            "papers": len(pubs), "citations": sum(cites), "h": h, "i10": i10,
            "first": sum(v["first"] for v in per.values()),
            "collab": sum(v["collab"] for v in per.values()),
            "chart": chart(per, True, "Refereed papers per year by authorship"),
            "cite_chart": chart(cit_year, False, "Citations to papers published each year"),
            "top_cited": top_cited,
            "journals": sorted(journals.items(), key=lambda kv: -kv[1])[:6],
        }

    def render_page(self, fm: dict, body: str, extra: dict | None = None) -> str:
        layout = fm.get("layout", "page")
        fm = dict(fm)
        fm.setdefault("banner_size", (self.site.get("banner_sizes") or {}).get(fm["slug"]))
        fm.setdefault("banner_position", (self.site.get("banner_positions") or {}).get(fm["slug"]))
        tpl = self.env.get_template(f"{layout}.html")
        banner_name = fm.get("banner") or (self.site.get("banners") or {}).get(fm["slug"])
        if isinstance(banner_name, list):   # first existing file wins
            banner_name = next((n for n in banner_name if find_image(n)), banner_name[-1])
        banner = self.image_src(banner_name) if banner_name else None
        logo = self.image_src(self.site.get("logo")) if self.site.get("logo") else None
        ctx = dict(site=self.site, page=fm, content=Markup(self.render_markdown(body)) if body.strip() else "",
                   banner=banner, logo=logo, href=self.href, asset=self.asset, md_inline=self.md_inline,
                   photo=self.figure(fm["photo"], "") if fm.get("photo") else None)
        if layout in ("home", "highlights"):
            limit = self.site.get("home_highlights", 6) if layout == "home" else None
            ctx["cards"], ctx["highlights_total"] = self.highlight_cards(limit)
        if layout == "home":
            ctx["programs"] = [{**p, "figure": self.figure(p["image"], p["title"], thumb=True),
                                "url": self.href(p["link"])} for p in fm.get("programs") or []]
            ctx["stats"] = self.pub_stats() if self.site.get("publication_stats", True) else None
        if layout == "members":
            ctx["members"] = load_yaml("members.yml", {})
        if layout == "publications":
            ctx["pubs_by_year"] = self.pubs_by_year()
            ctx["stats"] = self.pub_stats() if self.site.get("publication_stats", True) else None
        ctx.update(extra or {})
        return tpl.render(**ctx)


# --------------------------------------------------------------------------- outputs

def build_site(out: Path) -> Builder:
    b = Builder(preview=False)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(ASSETS, out / "assets", ignore=shutil.ignore_patterns("README*", ".*"))
    urls = []
    for fm, body in b.pages():
        html_out = b.render_page(fm, body)
        dest = out / "index.html" if fm["slug"] == "home" else out / fm["slug"] / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_out, encoding="utf-8")
        urls.append(fm["url"])
    # 404, redirects, sitemap, CNAME
    (out / "404.html").write_text(b.render_page({"slug": "404", "url": "", "title": "Page not found", "layout": "404"}, ""),
                                  encoding="utf-8")
    for old, new in (b.site.get("redirects") or {}).items():
        new = b.href(new)
        d = out / old.strip("/") / "index.html"
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={new}">'
                     f'<link rel="canonical" href="{new}"><a href="{new}">Moved here</a>', encoding="utf-8")
    domain = b.site.get("domain")
    if domain:
        (out / "CNAME").write_text(domain + "\n", encoding="utf-8")
        (out / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url><loc>https://{domain}{u}</loc></url>\n" for u in sorted(urls)) + "</urlset>\n",
            encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return b


PREVIEW_ROUTER = """
(function(){
  var secs=[].slice.call(document.querySelectorAll('[data-page]'));
  function show(){
    var k=(location.hash||'#home').slice(1).split('/')[0]||'home';
    if(!document.querySelector('[data-page="'+k+'"]')) k='home';
    secs.forEach(function(s){ s.hidden = s.getAttribute('data-page')!==k; });
    [].forEach.call(document.querySelectorAll('nav.tabs a'),function(a){
      if(a.getAttribute('href')==='#'+k) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current');
    });
    window.scrollTo(0,0);
  }
  window.addEventListener('hashchange',show); show();
})();
"""


def build_preview(out_file: Path) -> Builder:
    """Every page in one self-contained HTML file (for sharing a preview)."""
    b = Builder(preview=True)
    css = (ASSETS / "css" / "site.css").read_text(encoding="utf-8")
    sections = []
    for fm, body in b.pages():
        full = b.render_page(fm, body)
        soup = BeautifulSoup(full, "html.parser")
        banner = soup.select_one(".banner")
        main = soup.select_one("main")
        sections.append(f'<div data-page="{fm["slug"]}" hidden>{banner or ""}<main>{main.decode_contents()}</main></div>')
    shell = b.render_page({"slug": "home", "url": "/", "title": b.site.get("title"), "layout": "page"}, "",
                          {"inline_css": Markup(css), "extra_script": Markup(PREVIEW_ROUTER)})
    soup = BeautifulSoup(shell, "html.parser")
    soup.select_one(".banner").decompose()
    main = soup.select_one("main")
    main.replace_with(BeautifulSoup("".join(sections), "html.parser"))
    for a in soup.select("nav.tabs a"):
        a.attrs.pop("aria-current", None)
    for f in soup.select("iframe.map"):          # embedded frames are blocked in previews: link instead
        link = soup.new_tag("a", href=f["src"], target="_blank", rel="noopener")
        link.string = "Open the map (Google Maps)"
        wrap = soup.new_tag("p")
        wrap.append(link)
        f.replace_with(wrap)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(str(soup), encoding="utf-8")
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="write _preview/index.html instead of _site/")
    args = ap.parse_args()
    if args.preview:
        b = build_preview(ROOT / "_preview" / "index.html")
        print("preview -> _preview/index.html")
    else:
        b = build_site(ROOT / "_site")
        print(f"site -> _site/  ({sum(1 for _ in (ROOT/'_site').rglob('index.html'))} pages)")
    if b.missing_images:
        print(f"{len(b.missing_images)} image(s) not added yet (placeholders shown). "
              f"Run scripts/fetch_images.py, or see IMAGES.md.")


if __name__ == "__main__":
    sys.exit(main())
