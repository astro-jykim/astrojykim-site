#!/usr/bin/env python3
"""
Check that every piece of text and every link from the original Google Site
(_originals/) is present on the built site (_site/).

    python build.py && python scripts/check_completeness.py

Wording changes listed in scripts/migration/import_originals.py (EDITS) are applied
to the originals first, so only *unintended* differences are reported.
Exit code 1 if anything is missing.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "migration"))
from import_originals import EDITS  # noqa: E402

PAGES = {  # original -> built page
    "home": "index.html",
    "jae-young-kim": "jae-young-kim/index.html",
    "research": "research/index.html",
    "highlights": "highlights/index.html",
    "members": "members/index.html",
    "join-us": ["join-us/index.html", "positions-2027/index.html"],
    "contact": "contact/index.html",
    "2-3m-radio-telescope": "2-3m-radio-telescope/index.html",
}
WS = re.compile(r"[\s  -​  　﻿]+")
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def norm(s: str) -> str:
    return WS.sub(" ", unicodedata.normalize("NFC", s)).strip()


def expected(page: str):
    text = (ROOT / "_originals" / f"{page}.md").read_text(encoding="utf-8")
    for p, old, new, _n, _why in EDITS:
        if p == page:
            text = text.replace(old, new)
    text = re.sub(r"\(c\) Copyright Jae-Young Kim\. All rights reserved\. This webpage is customized for PC environments\.", "", text)
    text = re.sub(r"\[([^\]]*)\]", lambda m: "[" + m.group(1).replace("\n", " ") + "]", text)  # links split over lines
    fragments, links, images = [], [], 0
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("![") or line.startswith("[[EMBED"):
            if "sitesv-images" in line:
                images += 1
            continue
        line = re.sub(r"^(?:- )?#{1,4} ", "", line)
        line = re.sub(r"^- ", "", line)
        for label, url in LINK.findall(line):
            if url.startswith("#"):
                continue
            if label.strip() and label != "link":
                fragments.append(norm(label))
            links.append(url)
        for piece in LINK.split(line)[::3]:
            for part in piece.split(" | "):          # "2024-2026 | text" is shown as two columns
                part = norm(part)
                if len(re.findall(r"\w", part)) >= 2:
                    fragments.append(part)
    return fragments, links, images


def built(rel):
    if isinstance(rel, list):
        parts = [built(r) for r in rel]
        return " ".join(p[0] for p in parts), set().union(*(p[1] for p in parts)), sum(p[2] for p in parts)
    soup = BeautifulSoup((ROOT / "_site" / rel).read_text(encoding="utf-8"), "html.parser")
    for tag in soup.select("header, footer, script, style"):
        tag.decompose()
    text = norm(soup.get_text(" "))
    hrefs = {a["href"] for a in soup.find_all("a", href=True)} | {f["src"] for f in soup.find_all("iframe", src=True)}
    images = len(soup.select("main img")) + len(soup.select("main .ph"))
    return text, hrefs, images


def same_link(url: str, hrefs: set[str]) -> bool:
    if url in hrefs:
        return True
    u = url.rstrip("/")
    if url.startswith("/"):
        return u + "/" in hrefs or u in hrefs
    if "drive.google.com/file/d/" in url:  # /preview and /view point at the same file
        fid = url.split("/file/d/")[1].split("/")[0]
        return any(fid in h for h in hrefs)
    return False


def main() -> int:
    total_f = total_l = miss_f = miss_l = 0
    report = []
    for page, rel in PAGES.items():
        frags, links, img_orig = expected(page)
        text, hrefs, img_built = built(rel)
        # the members page renders "Name (detail), period" from data: compare with names bolded removed
        missing_f = [f for f in frags if f not in text]
        missing_l = [l for l in links if not same_link(l, hrefs)]
        total_f += len(frags); total_l += len(links)
        miss_f += len(missing_f); miss_l += len(missing_l)
        status = "OK  " if not missing_f and not missing_l else "MISS"
        report.append(f"{status} {page:22} text {len(frags)-len(missing_f):3}/{len(frags):<3}  "
                      f"links {len(links)-len(missing_l):3}/{len(links):<3}  images {img_built}/{img_orig}")
        for f in missing_f:
            report.append(f"       text  : {f[:110]}")
        for l in missing_l:
            report.append(f"       link  : {l[:110]}")
    print("\n".join(report))
    print(f"\nTotal: text {total_f-miss_f}/{total_f}, links {total_l-miss_l}/{total_l}")
    return 1 if (miss_f or miss_l) else 0


if __name__ == "__main__":
    sys.exit(main())
