#!/usr/bin/env python3
"""
NASA ADS -> data/publications.yml (+ new entries in data/highlights.yml)

    export ADS_TOKEN="..."                 # https://ui.adsabs.harvard.edu/user/settings/token
    python3 scripts/sync_ads.py            # preview only
    python3 scripts/sync_ads.py --write    # update the files

1. Fetch every paper for the ORCID below and rewrite data/publications.yml (with citations).
2. Find papers not yet on the Highlights page where you are among the first few authors
   (or that appeared in Nature / Science / Nature Astronomy) and add them at the TOP of
   data/highlights.yml. Papers already listed are recognised by bibcode or DOI, taken from
   the entry fields and from every link URL.

On GitHub this runs monthly (.github/workflows/ads-sync.yml) and opens a pull request.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import requests
import yaml

ORCID = "0000-0001-8229-7183"
FIRST_AUTHOR_WINDOW = 3                       # "among the first N authors"
ALWAYS = {"Nature", "Science", "Nature Astronomy"}
HIGHLIGHTS_SINCE = 2025                       # only newer papers are proposed as highlights
REFEREED_ONLY = True                          # publication list: refereed papers only
SKIP_DOCTYPES = {"abstract", "inproceedings", "proceedings", "eprint", "erratum", "catalog",
                 "software", "misc", "phdthesis", "mastersthesis", "techreport", "circular", "newsletter"}
SKIP_TITLE = re.compile(r"corrigendum|erratum|vizier|data catalog|online data", re.I)

ROOT = Path(__file__).resolve().parents[1]
PUBS = ROOT / "data" / "publications.yml"
HIGHLIGHTS = ROOT / "data" / "highlights.yml"
API = "https://api.adsabs.harvard.edu/v1/search/query"
FIELDS = "bibcode,title,author,year,pub,doi,citation_count,doctype,property,orcid_pub,orcid_user,orcid_other"


def fetch(token: str) -> list[dict]:
    out, start = [], 0
    while True:
        r = requests.get(API, headers={"Authorization": f"Bearer {token}"}, timeout=30,
                         params={"q": f"orcid:{ORCID}", "fl": FIELDS, "rows": 200, "start": start,
                                 "sort": "date desc"})
        if r.status_code == 401:
            sys.exit("ADS rejected the token. Check ADS_TOKEN.")
        r.raise_for_status()
        resp = r.json()["response"]
        out += resp["docs"]
        start += len(resp["docs"])
        if not resp["docs"] or start >= resp["numFound"]:
            return out


def my_position(doc: dict) -> int | None:
    for key in ("orcid_pub", "orcid_user", "orcid_other"):
        for i, v in enumerate(doc.get(key) or []):
            if v == ORCID:
                return i
    for i, name in enumerate(doc.get("author") or []):          # fallback: name match
        n = name.lower()
        if n.startswith("kim, j") and ("young" in n or "j.-y" in n or "j. -y" in n or "j.y" in n):
            return i
    return None


def ids_in(entry: dict) -> set[str]:
    ids = {entry.get("bibcode"), entry.get("doi")}
    for link in entry.get("links") or []:
        url = link.get("url", "")
        m = re.search(r"/abs/([^/]+)/", url)
        if m:
            ids.add(unquote(m.group(1)))
        m = re.search(r"(10\.\d{4,}/[^\s?#]+)", url)
        if m:
            ids.add(m.group(1).rstrip("/"))
        m = re.search(r"nature\.com/articles/(s[\w-]+)", url)
        if m:
            ids.add("10.1038/" + m.group(1))
        m = re.search(r"aanda\.org/articles/aa/(?:abs|full_html)/\d{4}/\d{2}/aa(\d+)-(\d{2})/", url)
        if m:
            ids.add(f"10.1051/0004-6361/20{m.group(2)}{m.group(1)}")
    return {i.lower() for i in ids if i}


def unwanted(doc: dict) -> bool:
    title = (doc.get("title") or [""])[0]
    return doc.get("doctype") in SKIP_DOCTYPES or bool(SKIP_TITLE.search(title))


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"<[^>]+>", "", t.lower())).strip()


def new_id(doc: dict, taken: set[str]) -> str:
    first = (doc.get("author") or ["paper"])[0].split(",")[0]
    base = re.sub(r"[^a-z]", "", first.lower()) + str(doc.get("year", ""))
    cand, n = base, 2
    while cand in taken:
        cand, n = f"{base}-{n}", n + 1
    taken.add(cand)
    return cand


def byline(doc: dict) -> str:
    authors = doc.get("author") or []
    lead = authors[0].split(",")[0] if authors else ""
    if len(authors) == 2:
        lead += " and " + authors[1].split(",")[0]
    elif len(authors) > 2:
        lead += " et al."
    return f"{lead} {doc.get('year', '')}, {doc.get('pub', '')}".strip()


def header_of(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").split("\n") if path.exists() else []
    head = []
    for l in lines:
        if l.startswith("#") or not l.strip():
            head.append(l)
        else:
            break
    return "\n".join(head).rstrip() + "\n\n" if head else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    token = os.environ.get("ADS_TOKEN", "").strip()
    if not token:
        sys.exit("Set ADS_TOKEN first (https://ui.adsabs.harvard.edu/user/settings/token).")

    docs = fetch(token)
    pubs = [{
        "title": (d.get("title") or [""])[0],
        "authors": (d.get("author") or [])[:10],
        "n_authors": len(d.get("author") or []),
        "year": int(d["year"]) if d.get("year") else None,
        "journal": d.get("pub"),
        "bibcode": d.get("bibcode"),
        "doi": (d.get("doi") or [None])[0],
        "citations": d.get("citation_count") or 0,
        "url": f"https://ui.adsabs.harvard.edu/abs/{d.get('bibcode')}/abstract",
    } for d in docs if not unwanted(d)
        and (not REFEREED_ONLY or "REFEREED" in (d.get("property") or []))]
    print(f"ADS: {len(docs)} records, {len(pubs)} kept for the publication list, "
          f"{sum(p['citations'] for p in pubs)} citations in total")

    highlights = yaml.safe_load(HIGHLIGHTS.read_text(encoding="utf-8")) or []
    known = set().union(*(ids_in(h) for h in highlights)) if highlights else set()
    known_titles = [norm_title(h.get("title", "")) for h in highlights]
    taken = {h["id"] for h in highlights}
    new = []
    for d in docs:
        if unwanted(d) or int(d.get("year") or 0) < HIGHLIGHTS_SINCE:
            continue
        t = norm_title((d.get("title") or [""])[0])
        if any(difflib.SequenceMatcher(None, t, k).ratio() > 0.85 for k in known_titles):
            continue
        ids = {(d.get("bibcode") or "").lower(), *[x.lower() for x in d.get("doi") or []]}
        if ids & known:
            continue
        pos = my_position(d)
        if not ((pos is not None and pos < FIRST_AUTHOR_WINDOW) or d.get("pub") in ALWAYS):
            continue
        new.append({"id": new_id(d, taken), "title": (d.get("title") or [""])[0],
                    "links": [{"text": byline(d), "url": f"https://ui.adsabs.harvard.edu/abs/{d['bibcode']}/abstract"}],
                    "bibcode": d.get("bibcode"),
                    **({"doi": d["doi"][0]} if d.get("doi") else {})})

    for n in new:
        print(f"  new highlight: [{n['id']}] {n['title'][:80]}")
    if not new:
        print("  no new highlights")
    if not args.write:
        print("(preview only — add --write to update the files)")
        return 0

    PUBS.write_text("# Generated by scripts/sync_ads.py — do not edit by hand.\n\n"
                    + yaml.safe_dump(pubs, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    if new:
        HIGHLIGHTS.write_text(header_of(HIGHLIGHTS)
                              + yaml.safe_dump(new + highlights, allow_unicode=True, sort_keys=False, width=100),
                              encoding="utf-8")
    print("files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
