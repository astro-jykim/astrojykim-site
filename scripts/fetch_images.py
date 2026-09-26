#!/usr/bin/env python3
"""
Download every image from the current Google Site into assets/img/, at full resolution,
with the file names the new site expects.

    python3 scripts/fetch_images.py

Google Sites image addresses expire after a while, so this script does not keep a
list of them. It reads the live pages each time, finds the images in page order,
and saves them under stable names. Standard library only — nothing to install.

Run it BEFORE editing or deleting anything on the Google Site: images are matched
to names by their position on each page.
"""

from __future__ import annotations

import argparse
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SITE = "https://www.astrojykim.com"
ROOT = Path(__file__).resolve().parents[1]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"

# Images inside each page, in the order they appear there.
INLINE = {
    "jae-young-kim": ["about/profile"],
    "research": ["research/figure-1", "research/centaurus-a", "research/effelsberg"],
    "highlights": [f"highlights/{i}" for i in [
        "ryu2026", "eht2025", "lee2025", "kim2025", "paraschos2024", "eht2024", "lu2023",
        "fuentes2023", "cui2023", "kim2023", "eht2022", "eht2019", "kim2018", "paraschos2023",
        "janssen2021", "kim2020", "paraschos2021", "kim2019", "paraschos2022", "larionov2020"]],
    "contact": ["contact/image-1", "contact/image-2"],
    "2-3m-radio-telescope": [f"telescope/{n}" for n in [
        "01-dish", "02-feedhorn", "03-dish-on-mount", "04-inspection", "05-receiver", "06-software",
        "07-side-view", "08-assembled", "09-pointing-test", "10-first-light"]],
}
# Page banners (the wide image behind each page title).
BANNERS = ["home", "research", "highlights", "members", "join-us", "contact", "2-3m-radio-telescope"]
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


class ImgFinder(HTMLParser):
    """Collect Google Sites image URLs, split into header (logo) and page body (<section>)."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.header, self.body = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            self.depth += 1
        if tag == "img":
            src = dict(attrs).get("src") or ""
            if "googleusercontent.com/sitesv-images" in src:
                (self.body if self.depth else self.header).append(src)

    def handle_endtag(self, tag):
        if tag == "section" and self.depth:
            self.depth -= 1


def get(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read(), r.headers.get_content_type()
    except (ssl.SSLError, urllib.error.URLError) as e:
        if "CERTIFICATE" not in str(e).upper():
            raise
        # Python from python.org on macOS may lack certificates: use the system curl instead
        out = subprocess.run(["curl", "-sSL", "-A", UA, "-D", "-", url], capture_output=True, check=True).stdout
        head, _, body = out.partition(b"\r\n\r\n")
        while head.startswith(b"HTTP/") and b" 30" in head.split(b"\r\n")[0]:
            head, _, body = body.partition(b"\r\n\r\n")
        m = re.search(rb"(?i)content-type:\s*([\w/+.-]+)", head)
        return body, (m.group(1).decode() if m else "application/octet-stream")


def full_res(url: str) -> str:
    return re.sub(r"=[wsh]\d+(-[a-z0-9-]+)?$", "", url) + "=s0"


def save(url: str, stem: str, out: Path) -> str:
    data, ctype = get(full_res(url))
    if not ctype.startswith("image/"):
        raise RuntimeError(f"not an image ({ctype})")
    dest = out / (stem + EXT.get(ctype, ".jpg"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    for old in dest.parent.glob(Path(stem).name + ".*"):      # replace a previous download
        old.unlink()
    dest.write_bytes(data)
    return f"{dest.relative_to(out)}  ({len(data) // 1024} KB)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "assets" / "img"), help="folder to save into")
    args = ap.parse_args()
    out = Path(args.out)
    ok = failed = 0
    logo_done = False

    for page in dict.fromkeys(list(INLINE) + BANNERS):
        try:
            html, _ = get(f"{SITE}/{page}")
        except Exception as e:
            print(f"!! could not open {SITE}/{page}: {e}")
            failed += len(INLINE.get(page, [])) + (page in BANNERS)
            continue
        html = html.decode("utf-8", "replace")
        finder = ImgFinder()
        finder.feed(html)

        jobs = []
        names = INLINE.get(page, [])
        if len(finder.body) != len(names):
            print(f"!! {page}: found {len(finder.body)} images, expected {len(names)}. "
                  f"The page may have changed; saving them as {page}/extra-N instead.")
            names = [f"{page}/extra-{i + 1}" for i in range(len(finder.body))]
        jobs += list(zip(finder.body, names))
        if page in BANNERS:
            m = re.search(r"background-image:\s*url\((?:&quot;|[\"'])?(https://[^)\"'&]*sitesv-images[^)\"'&]*)", html)
            if m:
                jobs.append((m.group(1), f"banners/{page}"))
            else:
                print(f"   {page}: no banner image found")
        if not logo_done and finder.header:
            jobs.append((finder.header[0], "site/logo"))
            logo_done = True

        for url, stem in jobs:
            try:
                print("   ok ", save(url, stem, out))
                ok += 1
            except Exception as e:
                print(f"!! {stem}: {e}")
                failed += 1

    print(f"\n{ok} images saved to {out}" + (f", {failed} failed" if failed else ""))
    print("Next: python3 build.py   (the site now uses these files)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
