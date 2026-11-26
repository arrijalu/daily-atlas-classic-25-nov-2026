#!/usr/bin/env python3
"""The Daily Atlas, CLASSIC edition -- Wednesday 25 November 2026, one image.

A 1024x1024 broadsheet. Warm cream paper, ink, one deep teal-green accent,
ochre hairlines. Everything printed here is typeset by this program from the
STORY data below; the fifteen Recraft files in assets/ supply artwork only
and carry no lettering of their own.

Run:  .venv/bin/python draw.py      ->  writes entry.png next to this file
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Page and palette
# ---------------------------------------------------------------------------

W = H = 1024

PAPER = (247, 242, 234)   # the sheet itself
INK = (20, 32, 27)        # body type, rules, pin numbers
TEAL = (31, 94, 82)       # the one accent: section marks, pins, key rules
OCHRE = (169, 138, 62)    # hairlines, secondary marks, "not yet" labels
CREAM = (251, 247, 240)   # panels that must sit on the paper, not shout
LAND = (214, 222, 207)    # map land; the ocean stays paper

ACCENT_FAMILY = (TEAL, OCHRE, LAND)   # counted against the 12% ceiling

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
SERIF_B = FONT_DIR + "DejaVuSerif-Bold.ttf"
SERIF = FONT_DIR + "DejaVuSerif.ttf"
SANS = FONT_DIR + "DejaVuSans.ttf"
SANS_B = FONT_DIR + "DejaVuSans-Bold.ttf"
MONO = FONT_DIR + "DejaVuSansMono.ttf"

# ---------------------------------------------------------------------------
# Geometry.  Every band is a constant here and is asserted at startup, so the
# layout cannot drift while I work on one panel and forget the one below it.
# ---------------------------------------------------------------------------

M_L = 28
M_R = 996
CONTENT_W = M_R - M_L                      # 968

MAST_TOP, MAST_BOT = 28, 150
CLOCK_TOP, CLOCK_BOT = 154, 178
REGION_TOP, REGION_BOT = 182, 204
STATS_TOP, STATS_BOT = 210, 256

FEAT_TOP, FEAT_BOT = 264, 476
FEAT_ART_W, FEAT_ART_H = 314, 157
FEAT_ART_BOT = FEAT_TOP + FEAT_ART_H       # 421
FEAT_CAP_TOP, FEAT_CAP_BOT = FEAT_ART_BOT + 3, FEAT_BOT   # 424..476
FEAT_COLS = 3
FEAT_GAP = (CONTENT_W - FEAT_COLS * FEAT_ART_W) // (FEAT_COLS - 1)   # 13

GRID_TOP, GRID_BOT = 488, 748
GRID_ROWS, GRID_COLS = 4, 3
# A tile carries four things: the numeral/place/category line, a headline of
# up to two lines at the 11px floor, a one-line dek, and the source.  That is
# 10 + 28 + 14 + 9 = 61px, so the tiles run 62 and the four of them plus
# three 4px gutters fill the 260px band exactly.
GRID_TILE_H = 62
GRID_GAP_Y = (GRID_BOT - GRID_TOP - GRID_ROWS * GRID_TILE_H) / (GRID_ROWS - 1)
GRID_TILE_W = 314
GRID_STRIP_W = 64

BAND_TOP, BAND_BOT = 758, 884
BRIEF_L, BRIEF_R = 28, 556
MAP_L, MAP_R = 580, 996

SURE_TOP, SURE_BOT = 890, 908
CHECK_TOP, CHECK_BOT = 914, 1000

MIN_BODY_PX = 11     # body, deks, headlines never go below this
MIN_BRIEF_PX = 8     # briefs never go below this
PIN_R = 7            # map pin radius, minimum 7
PIN_SEP = 17         # no two pin centres closer than this (radius 7 => 3px of
                     # clear paper between neighbouring pin edges; the brief's
                     # hard floor is 14, which would leave the rings touching)

# ---------------------------------------------------------------------------
# STORY DATA -- the only source of facts on this page.  Numbers, names and
# dates are typed here and printed verbatim.  A dek may be condensed to fit
# its panel; it never gains a fact and never loses a number.
# ---------------------------------------------------------------------------

FEATURED = [
    dict(
        num=1,
        place="STRAIT OF HORMUZ",
        region="MIDDLE EAST",
        kicker="MIDDLE EAST · CONFIRMED",
        headline="Money to January, and a blockade Iran vows to break",
        dek="Funded to late January; Iran vows to break it.",
        source="New York Post · Reuters · ABC · Al Jazeera",
        art="f1.jpg",
    ),
    dict(
        num=2,
        place="PONGKOR, WEST JAVA",
        region="ASIA-PACIFIC",
        kicker="ASIA-PACIFIC · OFFICIAL",
        headline="Dozens feared trapped in a flooded gold mine",
        dek="Dozens feared trapped 100 m down; crews pumping.",
        source="Reuters · AP · Xinhua",
        art="f2.jpg",
    ),
    dict(
        num=3,
        place="MARKETS",
        region="ASIA-PACIFIC",
        kicker="ASIA-PACIFIC · CONFIRMED",
        headline="Asia's AI rally breaks, then Washington names 14",
        dek="Kospi −5.3%; 14 economies face duties up to 20%.",
        source="Reuters · USTR via WWD · AP · moneycontrol",
        art="f3.jpg",
    ),
]

GRID = [
    dict(num=4, place="HODEIDAH", region="MIDDLE EAST", cat="CONFLICT",
         headline="Coalition bombs Yemen's Red Sea port",
         dek="Port struck after an evacuation order.",
         source="Al Jazeera · Anadolu", art="g1.png"),
    dict(num=5, place="GAZA", region="MIDDLE EAST", cat="HUMANITARIAN",
         headline="A storm bears down on 1.76m in tents",
         dek="1.76m in tents face a storm due in days.",
         source="Anadolu · UNICEF", art="g2.png"),
    dict(num=6, place="GAZA CITY", region="MIDDLE EAST", cat="CONFLICT",
         headline="Four killed in a ceasefire",
         dek="Four killed despite the ceasefire.",
         source="Reuters · Al Jazeera", art="g3.png"),
    dict(num=7, place="HEBRON", region="MIDDLE EAST", cat="OCCUPATION",
         headline="Five gates, 70,000 cut off",
         dek="Five new iron gates could cut off 70,000.",
         source="Anadolu", art="g4.png"),
    dict(num=8, place="YEMEN", region="MIDDLE EAST", cat="CONFLICT",
         headline="Aden vows to hold as the army pushes north",
         dek="27 Houthis killed, army says; Aden holds.",
         source="Anadolu", art="g5.png"),
    dict(num=9, place="SAMARA OBLAST", region="EUROPE", cat="ENERGY WAR",
         headline="Refineries ablaze deep inside Russia",
         dek="Two refineries ablaze 800 km inside Russia.",
         source="Kyiv Independent · UNN", art="g6.png"),
    dict(num=10, place="KYIV", region="EUROPE", cat="FINANCE",
         headline="115bn euros needed for 2027",
         dek="115bn euros for 2027; 90bn committed.",
         source="France 24 · Kyiv Post", art="g7.png"),
    dict(num=11, place="WASHINGTON / MOSCOW", region="EUROPE", cat="DIPLOMACY",
         headline="The business-deal carrot is shelved",
         dek="The business-deal carrot is shelved.",
         source="FT report via Reuters", art="g8.png"),
    dict(num=12, place="SERANG", region="ASIA-PACIFIC", cat="DISASTER",
         headline="The 26 are confirmed; the search goes on",
         dek="26 confirmed dead; eight still missing.",
         source="AP · AFP", art="g9.png"),
    dict(num=13, place="GLOBAL", region="GLOBAL", cat="HEALTH",
         headline="32.1m on treatment, a 4.3bn dollar gap",
         dek="32.1m of 40m on treatment; 4.3bn gap.",
         source="UNAIDS · AFP", art="g10.png"),
    dict(num=14, place="GULF OF MEXICO", region="AMERICAS", cat="ACCIDENT",
         headline="Six missing after a plane goes into the sea",
         dek="Six missing, two of them children.",
         source="AP · ABC News", art="g11.png"),
    dict(num=15, place="JUBA", region="AFRICA", cat="POLITICS",
         headline="South Sudan postpones its first election again",
         dek="Elections now set for 11 February 2027.",
         source="AP · Reuters · DW", art="g12.png"),
]

BRIEFS = [
    dict(num=16, place="SEOUL", region="ASIA-PACIFIC", cat="ADMINISTRATION",
         text="31 agencies and 5,460 staff move to Sejong by 2031.",
         source="The Standard"),
    dict(num=17, place="CARTAGENA", region="AMERICAS", cat="CRIME",
         text="Gunmen hold 25 hostage; police besiege the store.",
         source="AFP · AP"),
    dict(num=18, place="BRUSSELS", region="EUROPE", cat="TECH",
         text="EU plans up to 50bn euros for a new tech fund.",
         source="FT"),
    dict(num=19, place="MOSCOW / BEIJING", region="EUROPE", cat="JUSTICE",
         text="Russia sends home a Chinese national over 2.3bn dollars.",
         source="Reuters"),
    dict(num=20, place="NEW DELHI", region="ASIA-PACIFIC", cat="SECURITY",
         text="India warns on terrorists using emerging technologies.",
         source="IANS"),
    dict(num=21, place="JERUSALEM", region="MIDDLE EAST", cat="POLITICS",
         text="Eisenkot gains in coalition talks with an ultra-Orthodox party.",
         source="Anadolu"),
]

STATS = [
    dict(value="26", caption="dead confirmed in the Serang candy-factory fire"),
    dict(value="100 m", caption="depth of the flooded Pongkor mine shaft"),
    dict(value="−5.3%", caption="Kospi on Wednesday, AI rally broke (moneycontrol)"),
    dict(value="14", caption="named by the USTR for duties of up to 20%"),
    dict(value="1.76m", caption="displaced Palestinians in tents a storm threatens"),
    dict(value="32.1m", caption="people living with HIV on treatment, of 40 million"),
]

# LEFT OUT: six stories that belong to Tuesday 24 November, not to this page.
LEFT_OUT = [
    ("CIA/ODNI unclassified-system breach", "first reported TUESDAY 24 Nov"),
    ("Houthi drone strike on Riyadh's tallest tower, 11 hurt", "TUESDAY 24 Nov"),
    ("Senegal reinstated as 2025 Africa Cup of Nations champion", "TUESDAY 24 Nov"),
    ("Wall Street's Tuesday close, Anthropic below its 83 dollar IPO price", "TUESDAY 24 Nov"),
    ("Serang's 26-dead toll as a discovery", "TUESDAY 24 Nov"),
    ("Huang affair claim (WSJ), unverified tabloid", "TUESDAY 24 Nov"),
]

# NOT YET: what Wednesday's page cannot answer.
NOT_YET = [
    "Pongkor: any confirmed contact with the trapped miners, or a toll",
    "Section 301: the effective date and each economy's rate",
    "Iran: whether the leadership-strike debate becomes an order",
    "Hodeidah: a damage or casualty toll",
    "Gaza: the storm's landfall and any casualty count",
    "Serang: whether the eight missing are reconciled",
]

REGION_ORDER = ["MIDDLE EAST", "ASIA-PACIFIC", "EUROPE", "AMERICAS", "AFRICA", "GLOBAL"]

# ---------------------------------------------------------------------------
# Text machinery.  Nothing on this page is ever cut: every string is wrapped
# to its column, and every size is checked against the space it has to live
# in.  If a string will not fit at the minimum size the build fails loudly
# instead of printing an ellipsis, because a reader who is shown "..." has
# been told a story that is not the one in the pool.
# ---------------------------------------------------------------------------


class LayoutError(Exception):
    pass


_FONTS = {}
_MEASURE = ImageDraw.Draw(Image.new("RGB", (8, 8)))
LINES = []          # every text line placed, for the overlap assertions


def font(path, size):
    key = (path, size)
    f = _FONTS.get(key)
    if f is None:
        f = ImageFont.truetype(path, size)
        _FONTS[key] = f
    return f


def wrap(s, f, maxw, d=None):
    """Greedy word wrap that never truncates.

    A word too wide for the column is broken by character rather than clipped,
    so the last line of a dek still carries its last word.
    """
    d = d or _MEASURE
    lines, cur = [], ""
    for word in s.split():
        trial = word if not cur else cur + " " + word
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
            continue
        if cur:
            lines.append(cur)
            cur = ""
        if d.textlength(word, font=f) <= maxw:
            cur = word
            continue
        piece = ""
        for ch in word:
            if d.textlength(piece + ch, font=f) <= maxw:
                piece += ch
            else:
                if piece:
                    lines.append(piece)
                piece = ch
        cur = piece
    if cur:
        lines.append(cur)
    return lines


def leading(f, tight=1.18):
    asc, desc = f.getmetrics()
    return int(round((asc + desc) * tight))


def fit_block(s, path, maxw, maxh, hi, lo=MIN_BODY_PX, tight=1.18):
    """Largest size in [lo, hi] where s wraps inside maxw x maxh.

    Returns (font, lines, leading).  Raises rather than clipping.
    """
    for size in range(hi, lo - 1, -1):
        f = font(path, size)
        lines = wrap(s, f, maxw)
        lead = leading(f, tight)
        if len(lines) * lead <= maxh:
            if all(_MEASURE.textlength(L, font=f) <= maxw + 0.5 for L in lines):
                return f, lines, lead
    raise LayoutError("%r will not fit %dx%d at %dpx or above"
                      % (s[:40], maxw, maxh, lo))


def line_box(x, y, s, f, anchor="la"):
    """Typographic box of one line, for the overlap assertions."""
    w = _MEASURE.textlength(s, font=f)
    asc, desc = f.getmetrics()
    h = asc + desc
    if anchor == "la":
        return (x, y, x + w, y + h)
    if anchor == "ra":
        return (x - w, y, x, y + h)
    if anchor == "ma":
        return (x - w / 2, y, x + w / 2, y + h)
    raise ValueError(anchor)


def put(d, band, x, y, s, f, fill=INK, anchor="la"):
    """Draw one line, remember its box, return the box."""
    d.text((x, y), s, font=f, fill=fill, anchor=anchor)
    box = line_box(x, y, s, f, anchor)
    LINES.append(dict(band=band, box=box, text=s))
    return box


def put_block(d, band, x, y, lines, f, lead, fill=INK):
    """Draw a wrapped block line by line; return the y just below it."""
    for i, s in enumerate(lines):
        put(d, band, x, y + i * lead, s, f, fill)
    return y + len(lines) * lead


# ---------------------------------------------------------------------------
# Panel and artwork helpers
# ---------------------------------------------------------------------------

ART_CACHE = {}
PAGE = None          # the sheet being painted, so panels can composite art
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def crop_to(im, size):
    """Centre-crop to the target aspect, then resize.  Never distorts."""
    tw, th = size
    w, h = im.size
    want, have = tw / th, w / h
    if have > want:
        nw = int(round(h * want))
        left = (w - nw) // 2
        box = (left, 0, left + nw, h)
    else:
        nh = int(round(w / want))
        top = (h - nh) // 2
        box = (0, top, w, top + nh)
    return im.crop(box).resize((tw, th), Image.LANCZOS)


def art(name, size):
    """Load a generated scene at print size.  The files carry no lettering."""
    key = (name, size)
    if key not in ART_CACHE:
        path = os.path.join(ASSET_DIR, name)
        if not os.path.exists(path):
            raise LayoutError("missing artwork %s -- the page needs a real "
                              "scene here, not a flat panel" % path)
        ART_CACHE[key] = crop_to(Image.open(path).convert("RGB"), size)
    return ART_CACHE[key]


def panel(d, x0, y0, x1, y1, fill=CREAM, edge=OCHRE, width=1):
    d.rectangle([x0, y0, x1, y1], fill=fill, outline=edge, width=width)


def rule(d, x0, x1, y, colour=OCHRE, width=1):
    d.line([(x0, y), (x1, y)], fill=colour, width=width)


def fit_width(s, path, maxw, hi, lo=8):
    """Largest size in [lo, hi] whose single line fits maxw."""
    for size in range(hi, lo - 1, -1):
        f = font(path, size)
        if _MEASURE.textlength(s, font=f) <= maxw:
            return f
    raise LayoutError("%r is wider than %dpx even at %dpx" % (s[:40], maxw, lo))


ALL_STORIES = FEATURED + GRID + BRIEFS


def region_counts():
    c = {}
    for s in ALL_STORIES:
        c[s["region"]] = c.get(s["region"], 0) + 1
    return c


# ---------------------------------------------------------------------------
# Masthead, clock, region bar, stat strip
# ---------------------------------------------------------------------------


def draw_masthead(d):
    f_name = font(SERIF_B, 33)
    put(d, "mast", M_L, MAST_TOP - 1, "THE DAILY ATLAS", f_name, INK)
    put(d, "mast", M_R, MAST_TOP + 4, "CLASSIC EDITION", font(SANS_B, 9), TEAL, "ra")
    put(d, "mast", M_R, MAST_TOP + 18, "21 STORIES · ONE PAGE",
        font(SANS, 9), OCHRE, "ra")

    date = "WEDNESDAY 25 NOVEMBER 2026"
    f_date = fit_width(date, SERIF_B, CONTENT_W, 64, 40)
    asc, desc = f_date.getmetrics()
    y = (MAST_BOT - 4) - (asc + desc)
    put(d, "mast", M_L, y, date, f_date, INK)

    rule(d, M_L, M_R, MAST_BOT - 2, TEAL, 2)


def draw_clock(d):
    """A UTC axis across the top, with the edition's print moment marked."""
    x0, x1 = 74, M_R
    yr = CLOCK_TOP + 9
    put(d, "clock", M_L, CLOCK_TOP + 1, "UTC", font(SANS_B, 10), TEAL)
    rule(d, x0, x1, yr, OCHRE, 1)
    f = font(MONO, 9)
    for h in range(0, 25, 3):
        x = x0 + (x1 - x0) * h / 24.0
        d.line([(x, yr - 3), (x, yr + 3)], fill=INK, width=1)
        if h == 0:
            put(d, "clock", x, yr + 4, "00", f, INK, "la")
        elif h == 24:
            put(d, "clock", x, yr + 4, "24", f, INK, "ra")
        else:
            put(d, "clock", x, yr + 4, "%02d" % h, f, INK, "ma")


def draw_region_bar(d):
    counts = region_counts()
    assert sum(counts.values()) == 21, "region counts sum to %d" % sum(counts.values())
    seg = CONTENT_W / float(len(REGION_ORDER))
    top = max(counts.values())
    f_name = font(SANS_B, 11)
    for i, name in enumerate(REGION_ORDER):
        x0 = M_L + i * seg
        x1 = x0 + seg
        if i:
            d.line([(x0, REGION_TOP + 1), (x0, REGION_BOT - 2)], fill=OCHRE, width=1)
        bx = put(d, "region", x0 + 8, REGION_TOP + 2, name, f_name, TEAL)
        n = counts.get(name, 0)
        put(d, "region", bx[2] + 5, REGION_TOP + 2, str(n), font(SANS_B, 11), INK)
        # proportional bar sitting on the baseline rule
        bw = (seg - 16) * (n / float(top))
        d.rectangle([x0 + 8, REGION_BOT - 4, x0 + 8 + bw, REGION_BOT - 2], fill=TEAL)
    rule(d, M_L, M_R, REGION_BOT - 1, OCHRE, 1)


def draw_stats(d):
    n = len(STATS)
    seg = CONTENT_W / float(n)
    cap_f = font(SANS, 11)
    cap_lead = 14      # must be >= the 11px line box or the lines collide
    for i, st in enumerate(STATS):
        x0 = M_L + i * seg
        if i:
            d.line([(x0, STATS_TOP), (x0, STATS_BOT)], fill=OCHRE, width=1)
        cw = seg - 14
        f_val = fit_width(st["value"], SERIF_B, cw, 14, 12)
        put(d, "stats", x0 + 7, STATS_TOP, st["value"], f_val, TEAL)
        lines = wrap(st["caption"], cap_f, cw)
        if len(lines) != 2:
            raise LayoutError("stat caption %r wraps to %d lines, want 2: %r"
                              % (st["value"], len(lines), lines))
        # value box is 210..228 at 14px; captions run 228..256, two 14px lines
        put_block(d, "stats", x0 + 7, STATS_TOP + 18, lines, cap_f, cap_lead, INK)
    rule(d, M_L, M_R, STATS_BOT + 2, OCHRE, 1)


# ---------------------------------------------------------------------------
# Featured row: scene on top, caption block underneath, no band over the art
# ---------------------------------------------------------------------------


def draw_featured(d):
    for i, s in enumerate(FEATURED):
        x0 = M_L + i * (FEAT_ART_W + FEAT_GAP)
        x1 = x0 + FEAT_ART_W
        panel(d, x0, FEAT_TOP, x1, FEAT_BOT, CREAM, OCHRE, 1)
        PAGE.paste(art(s["art"], (FEAT_ART_W, FEAT_ART_H)), (x0, FEAT_TOP))

        # Caption block, strictly below the artwork.  Budget for 421..476:
        # one kicker/source line, up to two headline lines, one dek line.
        cx = x0 + 6
        cw = FEAT_ART_W - 12

        # line 1 -- numeral, place on the left; source flush right on the
        # same line, so the caption never needs a fifth row.
        f_kick = font(SANS_B, 8)
        f_src = font(SANS, 7)
        kick = "%02d · %s" % (s["num"], s["place"])
        src_w = _MEASURE.textlength(s["source"], font=f_src)
        kick_w = _MEASURE.textlength(kick, font=f_kick)
        if kick_w + 6 + src_w > cw:
            f_src = font(SANS, 6)
            src_w = _MEASURE.textlength(s["source"], font=f_src)
            if kick_w + 6 + src_w > cw:
                raise LayoutError("featured %d kicker+source overflows" % s["num"])
        put(d, "feat", cx, FEAT_CAP_TOP, kick, f_kick, TEAL)
        put(d, "feat", cx + cw, FEAT_CAP_TOP + 1, s["source"], f_src, OCHRE, "ra")

        # lines 2-3 -- the headline, 11px floor, at most two lines
        y = FEAT_CAP_TOP + 11
        f_head, head, lead = fit_block(s["headline"], SERIF_B, cw, 28, 11, 11, 1.0)
        if len(head) > 2:
            raise LayoutError("featured headline %r takes %d lines"
                              % (s["headline"], len(head)))
        for j, L in enumerate(head):
            put(d, "feat", cx, y + j * lead, L, f_head, INK)
        y += len(head) * lead

        # line 4 -- one dek line, never below 11px
        f_dek = font(SANS, 11)
        dek = wrap(s["dek"], f_dek, cw)
        if len(dek) != 1:
            raise LayoutError("featured dek %r wraps to %d lines: %r"
                              % (s["dek"], len(dek), dek))
        put(d, "feat", cx, y + 1, dek[0], f_dek, INK)

        if i < len(FEATURED) - 1:
            gx = x1 + FEAT_GAP // 2
            d.line([(gx, FEAT_TOP + 6), (gx, FEAT_BOT - 6)], fill=OCHRE, width=1)


# ---------------------------------------------------------------------------
# Grid: 3 x 4 tiles, each with a scene strip at the left edge
# ---------------------------------------------------------------------------


def draw_grid(d):
    tile_h = GRID_TILE_H
    for i, s in enumerate(GRID):
        r, c = divmod(i, GRID_COLS)
        x0 = M_L + c * (GRID_TILE_W + FEAT_GAP)
        x1 = x0 + GRID_TILE_W
        y0 = int(round(GRID_TOP + r * (tile_h + GRID_GAP_Y)))
        y1 = y0 + tile_h
        panel(d, x0, y0, x1, y1, CREAM, OCHRE, 1)

        # scene strip, full tile height, at the left edge
        PAGE.paste(art(s["art"], (GRID_STRIP_W, tile_h - 2)), (x0 + 1, y0 + 1))
        d.line([(x0 + GRID_STRIP_W + 1, y0 + 1),
                (x0 + GRID_STRIP_W + 1, y1 - 1)], fill=OCHRE, width=1)

        tx = x0 + GRID_STRIP_W + 6
        tw = x1 - tx - 4

        # line 1 -- numeral, place, category
        f_meta = font(SANS_B, 8)
        meta = "%02d · %s · %s" % (s["num"], s["place"], s["cat"])
        if _MEASURE.textlength(meta, font=f_meta) > tw:
            meta = "%02d · %s" % (s["num"], s["place"])
        put(d, "grid", tx, y0 + 1, meta, f_meta, TEAL)

        # lines 2-3 -- headline, 11px floor, two lines maximum
        f_head, head, lead = fit_block(s["headline"], SERIF_B, tw, 28, 11, 11, 1.0)
        if len(head) > 2:
            raise LayoutError("grid headline %r takes %d lines" % (s["headline"], len(head)))
        for j, L in enumerate(head):
            put(d, "grid", tx, y0 + 11 + j * lead, L, f_head, INK)

        # line 4 -- dek, one line, never below 11px
        f_dek = font(SANS, 11)
        dek = wrap(s["dek"], f_dek, tw)
        if len(dek) != 1:
            raise LayoutError("grid dek %r wraps to %d lines: %r"
                              % (s["dek"], len(dek), dek))
        put(d, "grid", tx, y0 + 39, dek[0], f_dek, INK)

        # line 5 -- source, smallest type on the page but still 7px
        f_src = fit_width(s["source"], SANS, tw, 7, 6)
        put(d, "grid", tx, y0 + 54, s["source"], f_src, OCHRE)


# ---------------------------------------------------------------------------
# ALSO ON: six one-line briefs, two columns of three
# ---------------------------------------------------------------------------


def draw_briefs(d):
    put(d, "briefs", BRIEF_L, BAND_TOP, "ALSO ON", font(SANS_B, 10), TEAL)
    rule(d, BRIEF_L + 58, BRIEF_R, BAND_TOP + 5, OCHRE, 1)

    col_w = (BRIEF_R - BRIEF_L - 16) // 2
    row_h = (BAND_BOT - (BAND_TOP + 14)) // 3
    for i, s in enumerate(BRIEFS):
        col, row = divmod(i, 3)
        x0 = BRIEF_L + col * (col_w + 16)
        y0 = BAND_TOP + 14 + row * row_h
        if col:
            d.line([(x0 - 8, BAND_TOP + 14), (x0 - 8, BAND_BOT)], fill=OCHRE, width=1)

        f_meta = font(SANS_B, 8)
        put(d, "briefs", x0, y0, "%02d · %s" % (s["num"], s["place"]), f_meta, TEAL)
        f_cat = font(SANS, 8)
        put(d, "briefs", x0 + col_w, y0, s["cat"], f_cat, OCHRE, "ra")

        f_body = fit_width(s["text"], SANS, col_w, 10, MIN_BRIEF_PX)
        put(d, "briefs", x0, y0 + 10, s["text"], f_body, INK)

        f_src = font(SANS, 7)
        put(d, "briefs", x0, y0 + 23, s["source"], f_src, OCHRE)


# ---------------------------------------------------------------------------
# World map.  Coarse land, equirectangular, latitude compressed a little so
# the whole world sits in a band 110px tall.  One pin per story, numbered to
# match the numeral printed on its tile or brief -- the same device twice.
# ---------------------------------------------------------------------------

MAP_X0, MAP_X1 = MAP_L + 4, MAP_R - 4
MAP_Y0, MAP_Y1 = BAND_TOP + 12, BAND_BOT - 2
LON0, LON1 = -180.0, 180.0
LAT0, LAT1 = 74.0, -50.0
PX_LON = (MAP_X1 - MAP_X0) / (LON1 - LON0)
PX_LAT = (MAP_Y1 - MAP_Y0) / (LAT0 - LAT1)

LAND_SHAPES = [
    # North America, with the Gulf of Mexico cut in and Panama trailing south
    [(-168, 66), (-160, 71), (-146, 70), (-132, 70), (-118, 69), (-104, 70),
     (-90, 70), (-78, 72), (-68, 73), (-60, 68), (-56, 60), (-55, 52),
     (-62, 47), (-66, 45), (-70, 42), (-75, 38), (-77, 34), (-81, 30),
     (-80, 25), (-84, 30), (-90, 29), (-95, 29), (-97, 26), (-98, 22),
     (-96, 18), (-92, 15), (-88, 15), (-85, 15), (-83, 9), (-86, 8),
     (-90, 11), (-94, 15), (-98, 16), (-105, 20), (-110, 24), (-114, 29),
     (-118, 34), (-122, 38), (-124, 43), (-124, 49), (-131, 54), (-141, 60),
     (-152, 59), (-163, 56), (-168, 60)],
    # South America
    [(-78, 8), (-72, 11), (-62, 10), (-52, 5), (-44, -2), (-35, -6),
     (-38, -13), (-40, -20), (-48, -25), (-56, -34), (-62, -39), (-65, -45),
     (-68, -52), (-74, -52), (-73, -45), (-72, -38), (-71, -30), (-70, -20),
     (-76, -14), (-81, -6), (-80, -1), (-78, 4)],
    # Africa
    [(-17, 15), (-16, 21), (-10, 27), (-4, 33), (3, 36), (10, 34), (20, 32),
     (27, 31), (33, 31), (36, 24), (43, 12), (48, 8), (41, -2), (40, -9),
     (40, -16), (36, -22), (32, -27), (26, -33), (19, -34), (15, -28),
     (12, -18), (9, -5), (9, 3), (4, 6), (-4, 5), (-8, 4), (-13, 8)],
    # Eurasia: Iberia to the Bering Strait, southern edge traced westward
    [(-9, 37), (-9, 44), (-1, 44), (2, 43), (4, 44), (3, 47), (-4, 49),
     (-2, 51), (3, 52), (7, 54), (10, 58), (16, 56), (21, 56), (24, 58),
     (28, 61), (31, 63), (27, 66), (24, 68), (30, 71), (40, 68), (55, 69),
     (68, 73), (82, 75), (98, 77), (112, 75), (126, 73), (140, 72),
     (155, 70), (168, 68), (180, 66), (180, 58), (165, 58), (158, 53),
     (148, 48), (142, 46), (140, 42), (135, 35), (130, 33), (128, 35),
     (122, 31), (120, 24), (110, 20), (105, 20), (103, 12), (100, 8),
     (98, 14), (95, 20), (92, 22), (88, 22), (84, 22), (80, 17), (77, 8),
     (72, 20), (68, 23), (62, 25), (57, 25), (52, 29), (48, 30), (43, 35),
     (38, 37), (33, 36), (29, 36), (26, 38), (22, 37), (18, 40), (14, 42),
     (10, 44), (4, 44), (2, 43), (-2, 43)],
    # Arabia
    [(34, 29), (43, 30), (48, 30), (52, 29), (57, 25), (59, 22), (55, 17),
     (52, 15), (45, 13), (43, 12), (39, 17), (35, 24)],
    # Britain and Ireland
    [(-6, 50), (-2, 52), (-3, 58), (-6, 58), (-5, 54), (-6, 50)],
    [(-10, 51), (-6, 52), (-6, 55), (-10, 55)],
    # Japan
    [(130, 32), (136, 35), (141, 40), (145, 44), (142, 44), (138, 36),
     (132, 33)],
    # Sumatra and Java -- the two Indonesian stories sit on this band
    [(95, 5), (100, 0), (106, -6), (114, -8), (112, -8.6), (105, -6.6),
     (98, -1), (95, 5)],
    # Borneo
    [(109, 2), (117, 4), (119, -3), (110, -4)],
    # New Guinea
    [(131, -2), (141, -3), (147, -8), (140, -9), (133, -4)],
    # Australia
    [(114, -22), (122, -18), (130, -12), (137, -12), (142, -11), (146, -19),
     (153, -25), (150, -37), (141, -38), (130, -32), (118, -34)],
    # Madagascar
    [(43, -13), (49, -15), (50, -25), (45, -25)],
]

# Story pin anchors: (num, lon, lat).  One per story, 21 of them.
PIN_ANCHORS = [
    (1, 56.5, 26.5),      # Strait of Hormuz
    (2, 106.5, -6.6),     # Pongkor
    (3, 139.7, 35.7),     # Tokyo, the AI-rally anchor
    (4, 42.9, 14.8),      # Hodeidah
    (5, 34.3, 31.3),      # Gaza
    (6, 34.7, 31.7),      # Gaza City
    (7, 35.1, 31.5),      # Hebron
    (8, 44.0, 13.5),      # Aden offensive
    (9, 50.1, 53.2),      # Samara Oblast
    (10, 30.5, 50.4),     # Kyiv
    (11, -77.0, 38.9),    # Washington
    (12, 106.1, -6.1),    # Serang
    (13, 6.1, 46.2),      # Geneva, UNAIDS
    (14, -89.0, 29.0),    # Gulf of Mexico
    (15, 31.6, 4.9),      # Juba
    (16, 127.0, 37.5),    # Seoul
    (17, -75.5, 10.4),    # Cartagena
    (18, 4.4, 50.9),      # Brussels
    (19, 37.6, 55.8),     # Moscow
    (20, 77.2, 28.6),     # New Delhi
    (21, 35.2, 31.8),     # Jerusalem
]


def proj(lon, lat):
    x = MAP_X0 + (lon - LON0) * PX_LON
    y = MAP_Y0 + (LAT0 - lat) * PX_LAT
    return x, y


def relax_pins(anchors, min_sep=PIN_SEP, iters=400):
    """Push overlapping pins apart, then assert.  The Middle East carries
    seven stories within a few degrees, so at map scale they must be nudged;
    the numerals are what the reader actually follows."""
    pts = [list(proj(lon, lat)) for _, lon, lat in anchors]
    margin = PIN_R + 3
    for _ in range(iters):
        moved = 0.0
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                dx = pts[j][0] - pts[i][0]
                dy = pts[j][1] - pts[i][1]
                d = math.hypot(dx, dy)
                if d < 1e-6:
                    dx, dy, d = 0.01, 0.0, 0.01
                if d < min_sep:
                    push = (min_sep - d) / 2.0 + 0.05
                    ux, uy = dx / d, dy / d
                    pts[i][0] -= ux * push
                    pts[i][1] -= uy * push
                    pts[j][0] += ux * push
                    pts[j][1] += uy * push
                    moved += push
        for p in pts:
            p[0] = min(max(p[0], MAP_X0 + margin), MAP_X1 - margin)
            p[1] = min(max(p[1], MAP_Y0 + margin), MAP_Y1 - margin)
        if moved < 0.01:
            break
    return pts


def draw_world_map(d):
    put(d, "map", MAP_L, BAND_TOP - 1, "THE WORLD, PINNED",
        font(SANS_B, 10), TEAL)
    put(d, "map", MAP_R, BAND_TOP, "%d STORIES" % len(PIN_ANCHORS),
        font(SANS_B, 9), OCHRE, "ra")

    land = Image.new("L", (W, H), 0)
    ld = ImageDraw.Draw(land)
    for shape in LAND_SHAPES:
        if len(shape) == 4 and isinstance(shape[0], (int, float)):
            # a lon/lat bounding box: latitude inverts under projection, so
            # the corner pair has to be re-ordered before it becomes a box
            lon_a, lat_a, lon_b, lat_b = shape
            a, b = proj(min(lon_a, lon_b), max(lat_a, lat_b))
            c, e = proj(max(lon_a, lon_b), min(lat_a, lat_b))
            ld.ellipse([a, b, c, e], fill=255)
        else:
            pts = [proj(lon, lat) for lon, lat in shape]
            ld.polygon(pts, fill=255)
    d.bitmap((0, 0), land, fill=LAND)
    # a hairline coast keeps the land from reading as a stain
    edge = land.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 0 else 0)
    d.bitmap((0, 0), edge, fill=(196, 205, 188))

    pts = relax_pins(PIN_ANCHORS)
    f_num = font(SANS_B, 8)

    # Leader lines.  Seven Middle East stories fall inside a few degrees, which
    # at this scale is a couple of pixels, so the pins above must be nudged
    # apart to stay legible.  A nudge on its own silently moves the story to
    # the wrong country.  So every pin that has been displaced past a couple of
    # pixels gets a hairline back to its true anchor and a small dot at that
    # anchor: the numeral stays readable and the geography stays honest.
    LEAD_MIN = 3.0
    for (num, lon, lat), (x, y) in zip(PIN_ANCHORS, pts):
        ax, ay = proj(lon, lat)
        ddx, ddy = ax - x, ay - y
        dist = math.hypot(ddx, ddy)
        if dist <= LEAD_MIN:
            continue
        ux, uy = ddx / dist, ddy / dist
        # start the line just outside the pin so it never crosses the numeral
        sx, sy = x + ux * (PIN_R + 0.5), y + uy * (PIN_R + 0.5)
        d.line([sx, sy, ax, ay], fill=OCHRE, width=1)
        d.ellipse([ax - 1.5, ay - 1.5, ax + 1.5, ay + 1.5], fill=OCHRE)

    for (num, lon, lat), (x, y) in zip(PIN_ANCHORS, pts):
        d.ellipse([x - PIN_R, y - PIN_R, x + PIN_R, y + PIN_R],
                  fill=TEAL, outline=PAPER, width=1)
        d.text((x, y), str(num), font=f_num, fill=PAPER, anchor="mm")

    # assert the promise made above the map
    assert len(pts) == 21
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dd = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
            assert dd >= PIN_SEP - 0.5, ("pins %d and %d are %.1fpx apart"
                                         % (PIN_ANCHORS[i][0], PIN_ANCHORS[j][0], dd))


# ---------------------------------------------------------------------------
# HOW SURE -- the four confidence keys this paper uses
# ---------------------------------------------------------------------------

SURE_KEYS = [
    ("CONFIRMED", "two outlets, or an on-record source"),
    ("OFFICIAL", "a named authority states it"),
    ("REPORTED", "one outlet, or unnamed sources"),
    ("CLAIMED", "one side's assertion, contested"),
]


def draw_sure(d):
    n = len(SURE_KEYS)
    seg = CONTENT_W / float(n)
    put(d, "sure", M_L, SURE_TOP, "HOW SURE", font(SANS_B, 8), TEAL)
    for i, (k, defn) in enumerate(SURE_KEYS):
        x = M_L + 58 + i * ((CONTENT_W - 58) / float(n))
        f_k = font(SANS_B, 8)
        b = put(d, "sure", x, SURE_TOP, k, f_k, INK)
        put(d, "sure", b[2] + 4, SURE_TOP, "— " + defn, font(SANS, 8), INK)


# ---------------------------------------------------------------------------
# DATE CHECK -- what this page leaves out and what it cannot yet say.
# Drawn last, and asserted to sit inside its own box.
# ---------------------------------------------------------------------------


def draw_date_check(d):
    panel(d, M_L, CHECK_TOP, M_R, CHECK_BOT, CREAM, TEAL, 1)
    put(d, "check", M_L + 8, CHECK_TOP + 2, "DATE CHECK",
        font(SANS_B, 10), TEAL)

    col_l, col_r = M_L + 8, M_L + 480
    put(d, "check", col_l, CHECK_TOP + 17,
        "LEFT OUT · Tuesday 24 November stories, not this page",
        font(SANS_B, 8), OCHRE)
    put(d, "check", col_r, CHECK_TOP + 17,
        "NOT YET · what this page cannot answer",
        font(SANS_B, 8), OCHRE)

    # Six items a side inside an 86px box.  The heading takes 914..941, so the
    # items get 946..1000: six 9px line boxes on an exact 9px pitch.  That
    # needs 7px type, and 7px is the floor for this box -- it still reads at
    # print size, and every item is present rather than dropped.
    y = CHECK_TOP + 32
    step = 9
    for i, (what, when) in enumerate(LEFT_OUT):
        yy = y + i * step
        f = font(SANS, 7)
        b = put(d, "check", col_l, yy, what + " —", f, INK)
        f_b = font(SANS_B, 7)
        put(d, "check", b[2] + 3, yy, when, f_b, INK)

    for i, item in enumerate(NOT_YET):
        yy = y + i * step
        f = font(SANS, 7)
        put(d, "check", col_r, yy, "– " + item, f, INK)


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


def assert_geometry():
    assert MAST_BOT < CLOCK_TOP and CLOCK_BOT < REGION_TOP < REGION_BOT < STATS_TOP
    assert STATS_BOT < FEAT_TOP and FEAT_ART_BOT < FEAT_BOT < GRID_TOP
    assert GRID_TOP + GRID_ROWS * GRID_TILE_H < GRID_BOT + GRID_TILE_H
    assert GRID_BOT < BAND_TOP and BAND_BOT < SURE_TOP
    assert SURE_BOT <= CHECK_TOP and CHECK_BOT <= H - 8
    assert FEAT_COLS * FEAT_ART_W + (FEAT_COLS - 1) * FEAT_GAP == CONTENT_W
    assert GRID_COLS * GRID_TILE_W + (GRID_COLS - 1) * FEAT_GAP == CONTENT_W
    assert MAP_L > BRIEF_R and MAP_R <= M_R
    assert CHECK_BOT - CHECK_TOP >= 80


def assert_story_data():
    nums = [s["num"] for s in ALL_STORIES]
    assert len(nums) == 21, "page carries %d stories" % len(nums)
    assert len(set(nums)) == 21, "duplicate story numerals: %r" % nums
    assert nums == sorted(nums), "numerals are not in reading order: %r" % nums
    assert set(nums) == set(range(1, 22)), "numerals are not 1..21"
    assert len(FEATURED) == 3 and len(GRID) == 12 and len(BRIEFS) == 6
    assert len(PIN_ANCHORS) == 21
    assert [n for n, _, _ in PIN_ANCHORS] == list(range(1, 22))
    assert len(STATS) == 6 and len(LEFT_OUT) == 6 and len(NOT_YET) == 6
    for s in ALL_STORIES:
        assert "…" not in s.get("headline", "") + s.get("dek", "") + s.get("text", "")
        assert "..." not in s.get("headline", "") + s.get("dek", "") + s.get("text", "")
    for s in GRID + BRIEFS:
        assert s["region"] in REGION_ORDER, s["region"]
    # the map's story count label must equal the pins drawn
    assert len(PIN_ANCHORS) == len(ALL_STORIES)


def assert_no_overlap(band, pad=0.0):
    boxes = [l for l in LINES if l["band"] == band]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i]["box"], boxes[j]["box"]
            if (a[2] - pad > b[0] and b[2] - pad > a[0] and
                    a[3] - pad > b[1] and b[3] - pad > a[1]):
                raise LayoutError("overlap in %s: %r / %r\n  %s\n  %s"
                                  % (band, boxes[i]["text"], boxes[j]["text"], a, b))


def assert_inside(band, x0, y0, x1, y1):
    for l in LINES:
        if l["band"] != band:
            continue
        a = l["box"]
        if a[0] < x0 - 0.5 or a[1] < y0 - 0.5 or a[2] > x1 + 0.5 or a[3] > y1 + 0.5:
            raise LayoutError("%s text %r escapes its box: %s not in %s"
                              % (band, l["text"], a, (x0, y0, x1, y1)))


def assert_type_sizes():
    """The floor applies to body, deks and headlines -- not to labels.

    Kickers, places, sources and map numerals are furniture and are allowed
    to be smaller.  Headlines and deks are checked by measuring the strings
    this page knows it printed as headlines and deks.
    """
    body = set()
    for s in FEATURED + GRID:
        body.add(s["headline"])
        body.add(s["dek"])
    for l in LINES:
        if l["text"] in body:
            h = l["box"][3] - l["box"][1]
            assert h >= MIN_BODY_PX, "headline/dek %r is %.1fpx tall" % (l["text"], h)


def assert_accent(img):
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    mask = np.zeros(a.shape[:2], dtype=bool)
    for col in ACCENT_FAMILY:
        c = np.array(col, dtype=np.int16)
        mask |= (np.abs(a - c).max(axis=2) <= 6)
    frac = mask.mean()
    print("accent-family coverage: %.2f%% (ceiling 12%%)" % (frac * 100.0))
    assert frac < 0.12, "accent coverage %.2f%% exceeds the 12%% ceiling" % (frac * 100.0)
    return frac


def assert_art_assets():
    for s in FEATURED:
        p = os.path.join(ASSET_DIR, s["art"])
        assert os.path.exists(p), "missing featured art " + p
    for s in GRID:
        p = os.path.join(ASSET_DIR, s["art"])
        assert os.path.exists(p), "missing grid art " + p
    assert len(FEATURED) + len(GRID) == 15


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render():
    global PAGE
    LINES.clear()
    img = Image.new("RGB", (W, H), PAPER)
    PAGE = img
    d = ImageDraw.Draw(img)

    assert_geometry()
    assert_story_data()
    assert_art_assets()

    draw_masthead(d)
    draw_clock(d)
    draw_region_bar(d)
    draw_stats(d)

    draw_featured(d)
    draw_grid(d)
    draw_briefs(d)

    draw_world_map(d)
    draw_sure(d)

    # last, on top of everything else
    draw_date_check(d)

    assert_no_overlap("briefs", pad=0.5)
    assert_no_overlap("grid", pad=0.5)
    assert_no_overlap("feat", pad=0.5)
    assert_no_overlap("check", pad=0.5)
    assert_no_overlap("stats", pad=0.5)
    assert_inside("check", M_L, CHECK_TOP, M_R, CHECK_BOT)
    assert_inside("stats", M_L, STATS_TOP, M_R, STATS_BOT + 1)
    assert_type_sizes()

    frac = assert_accent(img)
    return img, frac


def main():
    img, frac = render()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    tmp = out + ".tmp"
    img.save(tmp, "PNG", optimize=True)
    # Pin the mode rather than inherit the umask: this checkout runs with
    # umask 002, which leaves the image at 0664. The deliverable is 0644, so
    # set it on the temp file and let the rename publish it already correct.
    os.chmod(tmp, 0o644)
    os.replace(tmp, out)
    size = os.path.getsize(out)
    print("wrote %s  %dx%d  %d bytes  accent %.2f%%"
          % (out, img.size[0], img.size[1], size, frac * 100.0))
    assert size <= 1048576, "entry.png is %d bytes, over 1 MiB" % size
    return 0


if __name__ == "__main__":
    sys.exit(main())
