#!/usr/bin/env python3
"""
One-time migration:  _originals/*.md  ->  content/*.md + data/*.yml

_originals/ is a verbatim snapshot of the Google Site (2026-09-26), verified line
by line against the live pages. This script only *moves* that text into the new
structure. It never retypes it, so wording cannot drift by accident.

Anything beyond pure formatting is an explicit entry in EDITS below, applied with
an exact-match check (a stale edit fails loudly instead of silently doing nothing)
and written to CHANGES.md so every change to the original wording is reviewable.

Run once from the repository root:
    python scripts/migration/import_originals.py
After migration, edit content/ and data/ directly. Do not re-run this script;
it would overwrite later edits.
"""

from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[2]
ORIG = ROOT / "_originals"
CONTENT = ROOT / "content"
DATA = ROOT / "data"

# ---------------------------------------------------------------------------
# Wording changes. (page, old, new, expected_count, reason)
# Everything else the importer does is layout/formatting only.
# ---------------------------------------------------------------------------
EDITS = [
    ("jae-young-kim", "awareded", "awarded", 1, "Typo"),
    ("jae-young-kim", "Square Kilometer Array", "Square Kilometre Array", 2,
     "Official spelling; the Join Us page already uses “Kilometre”"),
    ("research", "to achieve an ultra-high angular resolution not be realized by any other method",
     "to achieve an ultra-high angular resolution that cannot be realized by any other method", 1,
     "Grammar"),
    ("join-us", "Student will conduct radio interferometry", "The student will conduct radio interferometry", 1,
     "Grammar"),
    ("join-us", "millimeter VLBI in 2030s", "millimeter VLBI in the 2030s", 1, "Grammar"),
    ("join-us", "(SKA) era by 2030s", "(SKA) era by the 2030s", 1, "Grammar"),
    ("members", "UNSIT", "UNIST", 2, "Typo"),
    ("members", "Deok-Hyeong Lee", "Deokhyeong Lee", 1, "Name spelling unified: Deokhyeong (confirmed)"),
    ("members", "Deokheyong Lee", "Deokhyeong Lee", 1, "Typo: heyong → hyeong (confirmed)"),
    ("members", "Chae-Won Kim", "Chaewon Kim", 1, "Name spelling unified without hyphen (requested)"),
    ("members", "Current research topic:", "", 1,
     "Label appeared on only one of the 27 entries; dropped for consistency"),
    ("highlights", "Wielgues", "Wielgus", 1, "Typo in co-author name (M. Wielgus)"),
    ("highlights", "Media echos", "Media echoes", 1, "Typo"),
    ("highlights", "[EHT Collaboration, 2019, ApJ](https://iopscience.iop.org/article/10.3847/2041-8213/ab0ec7)L",
     "[EHT Collaboration, 2019, ApJL](https://iopscience.iop.org/article/10.3847/2041-8213/ab0ec7)", 1,
     "The “L” of ApJL sat outside the link"),
    ("highlights", "[Paraschos, Mpisketzis, Kim JY et al.](https://ui.adsabs.harvard.edu/abs/2023A%26A...669A..32P/abstract)\n\n[2023, A&A](https://iopscience.iop.org/article/10.3847/2041-8213/ac6674)",
     "[Paraschos, Mpisketzis, Kim JY et al. 2023, A&A](https://ui.adsabs.harvard.edu/abs/2023A%26A...669A..32P/abstract)", 1,
     "Broken link fixed: “2023, A&A” pointed to the Sgr A* paper; merged into the correct ADS link"),
    ("highlights", "[Paraschos, Kim JY et al. 2021](https://www.aanda.org/articles/aa/full_html/2021/06/aa40776-21/aa40776-21.html), A&A",
     "[Paraschos, Kim JY et al. 2021, A&A](https://www.aanda.org/articles/aa/full_html/2021/06/aa40776-21/aa40776-21.html)", 1,
     "Journal name moved inside the link, like the other entries"),
    ("highlights", "[Kim JY et al. 2020, A&A\nPress Release](https://eventhorizontelescope.org/blog/something-is-lurking-in-the-heart-of-quasar-3c-279)",
     "[Kim JY et al. 2020, A&A](https://ui.adsabs.harvard.edu/abs/2020A%26A...640A..69K/abstract)[Press Release](https://eventhorizontelescope.org/blog/something-is-lurking-in-the-heart-of-quasar-3c-279)", 1,
     "The paper itself had no link (the whole line went to the EHT blog); added the ADS link, press release kept"),
    ("2-3m-radio-telescope", "digianl", "digital", 1, "Typo"),
    ("home", "(see [here](/join-us))", "(see [here](/positions-2027/))", 1,
     "The 2027 positions now have their own page"),
    ("2-3m-radio-telescope", "[contact me](https://www.astrojykim.com/contact)", "[contact me](/contact/)", 1,
     "Absolute link to the old site made relative"),
]

# Additions of new text (not in the original). Logged separately in CHANGES.md.
# --- 2026-09-27: changes requested after the first review --------------------------------
# Member group labels made clearer.
EDITS += [
    ("members", "Group lead", "Group Leader", 1, "Clearer group label"),
    ("members", "Graduates", "Graduate Students", 1, "Clearer group label"),
    ("members", "Undergraduates", "Undergraduate Researchers", 1, "Clearer group label"),
    ("members", "Advisory students", "Advisory Students", 1, "Clearer group label"),
    ("members", "Past supervisions, internships, or members", "Former Students and Interns", 1, "Clearer group label"),
]
# Join Us (general part) rewritten more concisely on request. The original wording stays in
# _originals/join-us.md; here each rewritten paragraph is simply dropped from the check.
_JOIN_US_REWRITTEN = ("We are always looking", "Our group welcomes", "Curiosity, scientific",
                      "UNIST provides substantial", "Various MSc", "Students considering",
                      "UNIST provides competitive", "We welcome undergraduate", "Typical internships",
                      "Students from outside", "We welcome inquiries", "While funded positions")
try:
    _orig = (Path(__file__).resolve().parents[2] / "_originals" / "join-us.md").read_text(encoding="utf-8")
    EDITS += [("join-us", line.strip(), "", 1, "Join Us rewritten more concisely (2026-09-27)")
              for line in _orig.split("\n") if line.strip().startswith(_JOIN_US_REWRITTEN)]
except FileNotFoundError:
    pass

ADDITIONS = [
    ("home", "One Korean line under the 2027 positions notice, linking to /ko/", "requested: 한글 병기"),
    ("join-us", "One Korean line under “NEW: Two Open Graduate Student Positions in 2027”", "requested: 한글 병기"),
    ("ko", "New short page /ko/: Korean summary of the 2027 positions, translated from the Join Us text", "requested: 임시 페이지"),
    ("research", "Page organised around the summary figure into three programs (direct imaging / multi-messenger / distant, faint and intermediate-mass black holes). Each program starts with the original sentence; one new paragraph and a row of related highlights added per program. All original text kept", "requested"),
    ("join-us", "The 2027 positions section (both projects) moved unchanged to a new page /positions-2027/; Join Us keeps the general text plus a one-line pointer", "requested"),
    ("site", "Group name in the header: “UNIST Observational Astrophysics Group”", "requested"),
    ("publications", "New page /publications/: ADS-generated list; until the first sync it shows the three buttons from Research", "new feature"),
]

# Layout-only changes worth mentioning (no wording change).
LAYOUT_NOTES = [
    "Footer: “This webpage is customized for PC environments.” dropped — the new site works on phones too. Copyright line kept.",
    "Join Us: the second “Join Us” heading (duplicate of the page title) removed.",
    "2.3m telescope: the four embedded Google Drive PDF viewers are now plain links to the same Drive files (same file names and captions).",
    "2.3m telescope: in-page table of contents re-pointed to the new section anchors.",
    "Highlights: cards keep the original order. Adjacent links (paper / press release) are shown as separate links.",
    "Members: entries rebuilt from data/members.yml in the same groups and order; each line renders exactly as before.",
    "Contact: address lines grouped into two blocks (English, Korean); email kept in the original ‘at’ form.",
]


def die(msg: str) -> None:
    sys.exit(f"import_originals: {msg}")


def read(page: str) -> str:
    return (ORIG / f"{page}.md").read_text(encoding="utf-8")


def apply_edits(page: str, text: str) -> str:
    for p, old, new, count, _ in EDITS:
        if p != page:
            continue
        found = text.count(old)
        if found != count:
            die(f"[{page}] expected {count}× {old[:60]!r}, found {found}")
        text = text.replace(old, new)
    return text


FOOTER = re.compile(
    r"\n*\(c\) Copyright Jae-Young Kim\. All rights reserved\. This webpage is customized for PC environments\.\s*$"
)
GHEAD = re.compile(r"(?m)^(?:- )?(#{2,4}) \[link\]\(#h\.[a-z0-9]+\)\n\n")
IMG = re.compile(r"!\[[^\]]*\]\((https?://[^)]+)\)")


def clean(text: str) -> str:
    """Formatting-only cleanup of Google Sites artefacts."""
    text = FOOTER.sub("\n", text)
    text = GHEAD.sub(lambda m: m.group(1) + " ", text)
    # headings with a manual line break: join continuation lines into the heading
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#{2,4} ", line):
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|- |!\[|\[\[)", lines[i + 1]):
                line = line.rstrip() + " " + lines[i + 1].strip()
                i += 1
        out.append(line.rstrip())
        i += 1
    text = "\n".join(out)
    text = re.sub(r"(?m)^[ \t\u00a0]+(?=\S)", "", text)          # stray indentation (would become code blocks)
    text = re.sub(r"\]\(/(join-us|highlights|contact|members|research|jae-young-kim)\)", r"](/\1/)", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def replace_images(text: str, names: list[str | None], page: str) -> str:
    """Replace Google image URLs in order with local file names (None = drop)."""
    urls = IMG.findall(text)
    if len(urls) != len(names):
        die(f"[{page}] {len(urls)} images in original, {len(names)} names in manifest")
    it = iter(names)

    def sub(m):
        name = next(it)
        return "" if name is None else f"![]({name})"

    return IMG.sub(sub, text)


def caption_from_next_paragraph(text: str, filename: str) -> str:
    """Turn  ![](f)\\n\\n<caption paragraph>  into  ![<caption>](f)."""
    pat = re.compile(r"!\[\]\(" + re.escape(filename) + r"\)\n\n(?P<cap>(?:(?!\n\n).)+)", re.S)
    m = pat.search(text)
    if not m:
        die(f"no caption paragraph after {filename}")
    cap = " ".join(m.group("cap").split())
    return text[: m.start()] + f"![{cap}]({filename})" + text[m.end():]


def front(**kw) -> str:
    return "---\n" + yaml.safe_dump(kw, allow_unicode=True, sort_keys=False, width=100) + "---\n\n"


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_home():
    t = apply_edits("home", read("home"))
    t = clean(t)
    lines = [l for l in t.split("\n") if l.strip()]
    assert lines[0] == "# Black Holes and Radio Astronomy"
    assert lines[1] == "# Ulsan National Institute of Science and Technology (UNIST)"
    welcome, intro, notice = lines[2], lines[3], lines[4]
    assert notice.startswith("NEW:")
    fm = front(
        title="Home",
        layout="home",
        banner="banners/home.jpg",
        hero_title=lines[0][2:],
        hero_subtitle=lines[1][2:],
        notice=notice,
        notice_ko="2027학년도 대학원생 2명을 모집합니다. [한국어 안내](/ko/)",
    )
    body = f"## {welcome}\n\n{intro}\n"
    (CONTENT / "home.md").write_text(fm + body, encoding="utf-8")


def page_about():
    t = apply_edits("jae-young-kim", read("jae-young-kim"))
    t = replace_images(t, ["about/profile.jpg"], "jae-young-kim")
    t = clean(t)
    t = t.replace("![](about/profile.jpg)\n\n", "")
    # first "heading" is empty (an anchor before the name block): drop it
    t = re.sub(r"^## Jae-Young Kim\n", "Jae-Young Kim\n", t, count=1)
    # sub-group labels inside Awards
    t = t.replace("\n\nIndividual\n\n", "\n\n### Individual\n\n", 1)
    t = t.replace("\n\nGroup awards\n\n", "\n\n### Group awards\n\n", 1)
    # list items that continue on a second line: join
    t = re.sub(r"(?m)^(- .+)\n(\((?:member|PIs)[^\n]+)$", r"\1 \2", t)
    # the name block: keep each line, but as one paragraph with line breaks
    head, rest = t.split("\n## Employment", 1)
    head_lines = [l for l in head.split("\n") if l.strip()]
    head_md = "\n".join(l + "  " for l in head_lines[:-2]) + "\n\n" + " · ".join(head_lines[-2:])
    body = head_md.strip() + "\n{: .profile-lines}\n\n## Employment" + rest
    fm = front(title="Jae-Young Kim", layout="page", photo="about/profile.jpg")
    (CONTENT / "jae-young-kim.md").write_text(fm + body, encoding="utf-8")


def page_research():
    t = apply_edits("research", read("research"))
    t = replace_images(t, ["research/figure-1.jpg", "research/centaurus-a.jpg", "research/effelsberg.jpg"], "research")
    t = clean(t)
    t = re.sub(r"^# Research\n\n", "", t)
    t = t.replace(")(in Korean).", ") (in Korean).")
    t = t.replace("(<hour)", "(&lt;hour)")          # a bare "<" would be read as an HTML tag
    t = caption_from_next_paragraph(t, "research/centaurus-a.jpg")
    # Effelsberg caption spans two lines in the original
    t = caption_from_next_paragraph(t, "research/effelsberg.jpg")
    # three publication links -> one row of buttons
    t = re.sub(
        r"(\[NASA ADS \(recommended\)\]\([^)]+\))\n\n(\[ORCID\]\([^)]+\))\n\n(\[Google Scholar\]\([^)]+\))",
        r"\1 \2 \3\n{: .buttons}", t)
    fm = front(title="Research", layout="page", banner="banners/research.jpg")
    (CONTENT / "research.md").write_text(fm + t, encoding="utf-8")


def page_join():
    t = apply_edits("join-us", read("join-us"))
    t = clean(t)
    t = re.sub(r"^# Join Us\n\n## Join Us\n\n", "", t)
    t = t.replace(
        "## NEW: Two Open Graduate Student Positions in 2027\n\n",
        "## NEW: Two Open Graduate Student Positions in 2027\n\n"
        "2027학년도 대학원생 2명을 모집합니다. [한국어 안내](/ko/)\n{: .ko-note}\n\n", 1)
    fm = front(title="Join Us", layout="page", banner="banners/join-us.jpg")
    (CONTENT / "join-us.md").write_text(fm + t, encoding="utf-8")


def page_contact():
    t = apply_edits("contact", read("contact"))
    t = replace_images(t, ["contact/image-1.jpg", "contact/image-2.jpg"], "contact")
    t = clean(t)
    t = re.sub(r"^# Contact\n\n", "", t)
    m = re.search(r"\[\[EMBED (\S+)\]\]", t)
    t = t.replace(m.group(0), f'<iframe class="map" src="{m.group(1)}" loading="lazy" title="Map: UNIST"></iframe>')
    # English block
    en = re.search(r"Jae-Young Kim\n\n(?:.+\n\n)*?Fax: TBA", t).group(0)
    t = t.replace(en, "  \n".join(l for l in en.split("\n") if l.strip()) + "\n{: .address}")
    ko = re.search(r"주소:[^\n]+\n\n(?:[^\n]+\n\n)*?이메일: [^\n]+", t).group(0)
    t = t.replace(ko, "  \n".join(l for l in ko.split("\n") if l.strip()) + "\n{: .address lang=ko}")
    fm = front(title="Contact", layout="page", banner="banners/contact.jpg")
    (CONTENT / "contact.md").write_text(fm + t, encoding="utf-8")


def page_telescope():
    t = apply_edits("2-3m-radio-telescope", read("2-3m-radio-telescope"))
    photos = ["telescope/01-dish.jpg", "telescope/02-feedhorn.jpg", "telescope/03-dish-on-mount.jpg",
              "telescope/04-inspection.jpg", "telescope/05-receiver.jpg", "telescope/06-software.jpg",
              "telescope/07-side-view.jpg", "telescope/08-assembled.jpg", "telescope/09-pointing-test.jpg",
              "telescope/10-first-light.jpg"]
    names = [None, None, None, None] + photos      # the first four are Google Drive file icons
    t = replace_images(t, names, "2-3m-radio-telescope")
    t = clean(t)
    t = re.sub(r"^# 2\.3m radio telescope\n\n", "", t)
    # table of contents -> new anchors
    for label, slug in [("IMPORTANT NOTE", "important-note"), ("Introduction", "introduction"),
                        ("Useful literature and memos", "useful-literature-and-memos"),
                        ("Manuals for the telescope", "manuals-for-the-telescope"), ("Pictures", "pictures")]:
        t = re.sub(r"\[" + re.escape(label) + r"\]\(#h\.[a-z0-9]+\)", f"[{label}](#{slug})", t, count=1)
    t = re.sub(r"(\[IMPORTANT NOTE\]\(#important-note\))\n\n(\[Introduction\][^\n]+)\n\n(\[Useful[^\n]+)\n\n(\[Manuals[^\n]+)\n\n(\[Pictures\][^\n]+)",
               r"\1 · \2 · \3 · \4 · \5\n{: .toc}", t)
    # Manuals: Google Sites file cards -> list. Captions follow each card as a "heading".
    pat = re.compile(
        r"\[\[EMBED https://drive\.google\.com/file/d/(?P<id>[\w-]+)/preview\]\]\n\n"
        r"(?P<fname>\S+\.pdf)\n\n\[\[EMBED https://drive\.google\.com/open\?id=[\w-]+\]\]\n\n"
        r"## (?P<cap>[^\n]+)\n\n")
    items = [f"- [{m['fname']}](https://drive.google.com/file/d/{m['id']}/view) — {m['cap']}" for m in pat.finditer(t)]
    if len(items) != 4:
        die(f"telescope manuals: parsed {len(items)} of 4")
    start = pat.search(t).start()
    end = list(pat.finditer(t))[-1].end()
    t = t[:start] + "\n".join(items) + "\n\n" + t[end:]
    for f in photos:
        t = caption_from_next_paragraph(t, f)
    # consecutive figures -> gallery block
    figs = "\n\n".join(r"!\[[^\]]+\]\(" + re.escape(f) + r"\)" for f in photos)
    m = re.search(figs, t)
    if not m:
        die("telescope: photos are not consecutive")
    t = t[: m.start()] + '<div class="gallery" markdown="1">\n\n' + m.group(0) + "\n\n</div>" + t[m.end():]
    fm = front(title="2.3m radio telescope", layout="page", banner="banners/2-3m-radio-telescope.jpg")
    (CONTENT / "2-3m-radio-telescope.md").write_text(fm + t, encoding="utf-8")


# ---------------------------------------------------------------------------
# Data pages
# ---------------------------------------------------------------------------

HL_IDS = ["ryu2026", "eht2025", "lee2025", "kim2025", "paraschos2024", "eht2024", "lu2023",
          "fuentes2023", "cui2023", "kim2023", "eht2022", "eht2019", "kim2018", "paraschos2023",
          "janssen2021", "kim2020", "paraschos2021", "kim2019", "paraschos2022", "larionov2020"]

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def ids_from_url(url: str) -> dict:
    out = {}
    m = re.search(r"ui\.adsabs\.harvard\.edu/abs/([^/]+)/", url)
    if m:
        out["bibcode"] = unquote(m.group(1))
    m = re.search(r"nature\.com/articles/(s[\w-]+)", url)
    if m:
        out["doi"] = "10.1038/" + m.group(1)
    m = re.search(r"iopscience\.iop\.org/article/(10\.\d+/[^\s?#]+)", url)
    if m:
        out["doi"] = m.group(1)
    m = re.search(r"aanda\.org/articles/aa/(?:abs|full_html)/\d{4}/\d{2}/aa(\d+)-(\d{2})/", url)
    if m:
        out["doi"] = f"10.1051/0004-6361/20{m.group(2)}{m.group(1)}"
    m = re.search(r"academic\.oup\.com/mnras/article/(\d+)/\d+/(\d+)/", url)
    if m:
        out["bibcode_hint"] = f"MNRAS {m.group(1)}, {m.group(2)}"
    return out


def data_highlights():
    t = apply_edits("highlights", read("highlights"))
    t = replace_images(t, [f"highlights/{i}.jpg" for i in HL_IDS], "highlights")
    t = FOOTER.sub("\n", t)
    t = re.sub(r"^# Highlights\n\n", "", t)
    blocks = re.split(r"(?m)^!\[\]\(highlights/[\w]+\.jpg\)\n\n", t)[1:]
    if len(blocks) != len(HL_IDS):
        die(f"highlights: {len(blocks)} blocks")
    entries = []
    for hid, block in zip(HL_IDS, blocks):
        paras = [" ".join(p.split()) for p in block.strip().split("\n\n") if p.strip()]
        title, rest = paras[0], paras[1:]
        links, notes = [], []
        for p in rest:
            stripped = LINK.sub("", p).strip(" ,.;·")
            if not stripped:                                  # paragraph made only of links
                links += [{"text": a, "url": u} for a, u in LINK.findall(p)]
            else:
                notes.append(p)
        e = OrderedDict(id=hid, title=title)
        e["links"] = links
        if notes:
            e["notes"] = notes
        for l in links:
            for k, v in ids_from_url(l["url"]).items():
                e.setdefault(k, v)
        entries.append(dict(e))
    # extra identifiers so the ADS sync recognises papers linked via publisher pages
    extra = {"kim2020": {"bibcode": "2020A&A...640A..69K"},
             "larionov2020": {"bibcode": "2020MNRAS.492.3829L"}}
    for e in entries:
        e.update(extra.get(e["id"], {}))
        e.pop("bibcode_hint", None)
    header = (
        "# =============================================================================\n"
        "# Highlights — rendered in this order on /highlights/ (and the first 6 on Home).\n"
        "#\n"
        "# Image: put a file named <id>.jpg (or .png/.webp) in assets/img/highlights/.\n"
        "#        No setting needed here; the file name is the link.\n"
        "# links: shown under the title (paper, press release, ...).\n"
        "# notes: optional extra lines; Markdown links allowed.\n"
        "# bibcode / doi: used by scripts/sync_ads.py to recognise papers already listed.\n"
        "# =============================================================================\n\n")
    (DATA / "highlights.yml").write_text(
        header + yaml.safe_dump(entries, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


PERSON = re.compile(r"^(?P<name>[^()]+?) \((?P<detail>[^)]*)\), (?P<period>.*\d{4}.*)$")


def data_members():
    t = apply_edits("members", read("members"))
    t = FOOTER.sub("\n", t)
    t = re.sub(r"^# Members\n\n", "", t)
    intro, rest = t.split("\n\nGroup lead\n\n", 1)
    labels = ["Group lead", "Graduates", "Undergraduates", "Advisory students", "Alumni",
              "Past supervisions, internships, or members"]
    rest = "Group lead\n\n" + rest
    groups = []
    parts = re.split(r"(?m)^(" + "|".join(re.escape(l) for l in labels) + r")\n\n", rest)
    it = iter(parts[1:])
    for label, chunk in zip(it, it):
        items = [" ".join(l[2:].split()) for l in chunk.strip().split("\n\n") if l.startswith("- ")]
        people = []
        for item in items:
            m = PERSON.match(item)
            if label == "Group lead":
                people.append({"name": item, "link": "/jae-young-kim/"})
            elif m:
                people.append({"name": m["name"].strip(), "detail": m["detail"].strip(),
                               "period": " ".join(m["period"].split())})
            elif people and "topic" not in people[-1]:
                people[-1]["topic"] = item.strip()
            else:
                die(f"members: cannot place line {item!r}")
        groups.append({"label": label, "people": people})
    header = (
        "# =============================================================================\n"
        "# Members — rendered on /members/ in this order.\n"
        "# Each person renders as:  Name (detail), period   followed by the topic.\n"
        "# To add someone, copy an entry. To move someone to Alumni, cut & paste the entry.\n"
        "# =============================================================================\n\n")
    doc = {"intro": " ".join(intro.split()).replace("](/contact)", "](/contact/)"), "groups": groups}
    (DATA / "members.yml").write_text(
        header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


# ---------------------------------------------------------------------------
# New pages
# ---------------------------------------------------------------------------

def page_ko():
    fm = front(title="2027학년도 대학원생 모집", layout="page", lang="ko", banner="banners/join-us.jpg",
               nav=False)
    body = """UNIST 물리학과 김재영 교수 연구실에서 **2027년 입학 석박사통합과정 또는 박사과정 학생 2명**을 모집합니다.
전파 관측으로 블랙홀 활동과 상대론적 제트, 은하 진화의 관계를 연구하며, 차세대 EHT/mm-VLBI와 SKA 과학을 위한 전문성을 기르게 됩니다.

**모집 분야**

1. **초대질량블랙홀 근처의 동역학과 자기장** — M87 등 가까운 활동은하핵을 대상으로 EHT·VLBI 관측, 편광 분석
2. **전형적인 전파은하를 넘어서는 블랙홀 엔진** — 나선은하 DRAGN 등 특이한 활동은하핵을 SKA 선행 서베이로 탐색

물리·천문뿐 아니라 공학, 컴퓨터과학, 응용수학 등 다양한 전공에서 지원할 수 있으며, 천문학 연구 경험은 필요하지 않습니다.
자리가 채워질 때까지 지원을 받습니다. 미리 연락해서 프로젝트와 입학 절차를 상의하기를 권합니다.

자세한 내용은 [Join Us](/join-us/) (영문) · 연락: jaeyoungkim at unist.ac.kr
"""
    (CONTENT / "ko.md").write_text(fm + body, encoding="utf-8")


def page_publications():
    t = read("research")
    m = re.search(r"\[NASA ADS \(recommended\)\]\([^)]+\)\n\n\[ORCID\]\([^)]+\)\n\n\[Google Scholar\]\([^)]+\)", t)
    buttons = m.group(0).replace("\n\n", " ") + "\n{: .buttons}"
    fm = front(title="Publications", layout="publications", banner="banners/research.jpg")
    (CONTENT / "publications.md").write_text(fm + buttons + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------

def write_changes():
    lines = ["# Changes to the original wording", "",
             "Everything on the new site comes from `_originals/` (verbatim snapshot of the Google Site,",
             "2026-09-26). Below is every place where the wording was changed or added.",
             "Layout-only changes are listed at the end.", "",
             "## Edits", "", "| Page | Before | After | Why |", "|---|---|---|---|"]
    esc = lambda s: s.replace("|", "\\|").replace("\n", " ⏎ ")
    for p, old, new, n, why in EDITS:
        short = lambda s: esc(s if len(s) < 90 else s[:87] + "…")
        lines.append(f"| {p} | {short(old)} | {short(new) or '*(removed)*'} | {esc(why)}{' (×%d)' % n if n > 1 else ''} |")
    lines += ["", "## Additions", "", "| Page | What | Why |", "|---|---|---|"]
    for p, what, why in ADDITIONS:
        lines.append(f"| {p} | {what} | {why} |")
    lines += ["", "## Layout only", ""] + [f"- {n}" for n in LAYOUT_NOTES] + [""]
    (ROOT / "CHANGES.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    CONTENT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    page_home(); page_about(); page_research(); page_join(); page_contact(); page_telescope()
    data_highlights(); data_members()
    page_ko(); page_publications()
    write_changes()
    print("content/:", ", ".join(sorted(p.name for p in CONTENT.glob("*.md"))))
    print("data/:   ", ", ".join(sorted(p.name for p in DATA.glob("*.yml"))))
    print(f"CHANGES.md: {len(EDITS)} edits, {len(ADDITIONS)} additions")


if __name__ == "__main__":
    main()
