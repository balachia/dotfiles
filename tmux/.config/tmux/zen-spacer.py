#!/usr/bin/env python3
# stdlib only, on purpose: runs on whatever system python3 is around.
"""zen-spacer: animated spacer panes for zen.sh.

Usage: zen-spacer.py <style>   (ZEN_SIDE=left|right is set by zen.sh)

Styles:
  garden  a yard at night, 1-bit dither-shaded in braille, one scene across
          the window: moon, stars, picket fence, a tree, a meadow and
          flowers swaying in the shared wind, a random tree (oak, pine,
          willow, birch; @zen-tree) in a random season (summer, autumn,
          winter = bare + snow; @zen-season) and weather (clear, rain, snow;
          @zen-weather), leaves blowing off it
          and behind the center pane, fireflies, and an "IN THIS HOST WE
          BELIEVE" yard sign with random slogans. Ink follows the season
          unless @zen-ink is set.
  coffee  a desk at night, 1-bit dither-shaded in braille: a steaming mug
          with a printed label on one side, a banker's lamp under a wall
          clock on the other, everything lit by the lamp (@zen-ink color).
          Side picked at random per toggle; the coffee goes cold after 45
          minutes.
  matrix  green falling-glyph rain.
  sysrain matrix rain that reveals live system activity planted in the
          glyph grid: process names (cpu, red), memory growth/residents
          (mem, cyan), network peers (net, yellow), GPU load (magenta).
          Density tracks pressure.
  transit line diagrams, one line per side (@zen-transit, default
          "Red,Orange"): live MBTA trains polled every 20s from
          api-v3.mbta.com, or "sg:NSL,EWL" for schedule-shaped Singapore MRT.
  host    matrix rain parting around block letters: hostname on the left,
          username on the right (letters now and then dissolve into glyphs
          and snap back).

Sync: the two spacers never talk. Each asks tmux where it sits in the window,
and everything that crosses between them is a pure function of (world
position, wall-clock time, hashed id), so both compute the same world.

Live restyle: once a second the spacer re-reads @zen-style / @zen-spacer and,
if they changed, has zen.sh respawn it with the new command.

Only the 16 ANSI colors are used, so it follows the terminal palette.
q or C-d quits (same as the blank spacer).
"""
import collections
import curses
import functools
import glob
import getpass
import json
import math
import os
import random
import re
import socket
import struct
import subprocess
import textwrap
import sys
import threading
import time
import urllib.parse
import urllib.request
import zlib

HERE = os.path.dirname(os.path.realpath(__file__))


def tmux(*args):
    try:
        return subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def opt(name):
    """A tmux user option as this pane sees it: pane, then window, then
    session, then global, so `setw @zen-style …` themes one window."""
    pane = os.environ.get("TMUX_PANE")
    return tmux("display", "-p", *(["-t", pane] if pane else []), f"#{{@{name}}}")


class Screen:
    def __init__(self, scr):
        self.scr = scr
        # curses may notice lines moving (the docent's scrolling transcript)
        # and use the terminal's scroll or insert/delete: that drags along
        # the cells we write around it and leaves blank rows. Plain redraws only.
        scr.idlok(False)
        scr.idcok(False)
        self.raw, self.shown = {}, {}
        self.resize()

    def resize(self):
        self.h, self.w = self.scr.getmaxyx()
        self.shown, self.texts = {}, {}  # the screen was cleared: draw every raw cell afresh
        # where this pane sits in the window, for window-wide ("world") scenes
        geo = tmux("display", "-p", "-t", os.environ.get("TMUX_PANE", ""), "#{pane_left} #{window_width}").split()
        self.x0, self.world_w = (int(geo[0]), int(geo[1])) if len(geo) == 2 else (0, self.w)

    def put(self, y, x, s, color, attr=0):
        # skip the bottom-right cell: writing there makes curses raise
        if 0 <= y < self.h and 0 <= x < self.w and not (y == self.h - 1 and x == self.w - 1):
            if len(s) == 1 and s >= "\U0001cc00":
                # Unicode 16 block characters (octants): macOS's libc doesn't
                # know their width, so curses would blank them. curses gets a
                # space and refresh() writes the real character around it.
                self.raw[(y, x)] = (s, color, attr)
                s = " "
            else:
                for i in range(len(s)):
                    self.raw.pop((y, x + i), None)
            try:
                self.scr.addstr(y, x, s, curses.color_pair(color + 1) | attr)
            except curses.error:
                pass

    def put_sgr(self, y, x, ch, sgr):
        """One character with its own SGR attributes (e.g. "0;38;5;178"),
        written around curses like the octants: curses only does 8 colours."""
        if 0 <= y < self.h and 0 <= x < self.w and not (y == self.h - 1 and x == self.w - 1):
            self.raw[(y, x)] = (ch, sgr, 0)
            try:
                self.scr.addstr(y, x, " ")
            except curses.error:
                pass

    def refresh(self):
        # curses repaints a line whose text changed, and may do it in ways
        # (clearing from the left, rewriting the run) that wipe our raw cells
        # on it, which it thinks are blank: find those lines, redo their cells
        lines = {}
        for y in {y for (y, x) in self.raw} | {y for (y, x) in self.shown}:
            try:
                lines[y] = self.scr.instr(y, 0)
            except curses.error:
                pass
        changed = {y for y, text in lines.items() if self.texts.get(y) != text}
        self.texts = lines
        self.scr.refresh()
        # where curses just left the terminal's cursor, and believes it still is:
        # read it now, as inch() below moves the window's cursor (so do the
        # instr() above, but before the refresh). Putting the cursor back
        # anywhere else makes curses' next relative moves (ESC M, CSI n C)
        # land off by a row/columns and garble the docent's lines.
        cy, cx = self.scr.getyx()
        out = []
        # a raw cell gone since last frame is a space to curses both times, so
        # curses never repaints it: blank it ourselves. (Not by redrawing its
        # whole line: in a fade most lines lose a cell every frame, and line
        # redraws flash the background.) Skip cells curses has drawn into.
        for (y, x) in self.shown:
            if (y, x) not in self.raw and self.scr.inch(y, x) & curses.A_CHARTEXT == 32:
                out.append(f"\x1b[{y + 1};{x + 1}H\x1b[0m ")
        if self.raw or out:
            for (y, x), cell in self.raw.items():
                if self.shown.get((y, x)) == cell and y not in changed:
                    continue  # already on screen, on a line curses left alone
                ch, color, attr = cell
                sgr = color if isinstance(color, str) else (
                    "0;3%d" % color + (";1" if attr & curses.A_BOLD else "") + (";2" if attr & curses.A_DIM else ""))
                out.append(f"\x1b[{y + 1};{x + 1}H\x1b[{sgr}m{ch}")
            out.append(f"\x1b[0m\x1b[{cy + 1};{cx + 1}H")  # leave things as curses left them
            os.write(1, "".join(out).encode())
        self.shown, self.raw = self.raw, {}


# ---------------------------------------------------------------- garden



GUST_PERIOD = 20.0


@functools.lru_cache(maxsize=1024)
def gusty(bucket):
    return random.Random(bucket).random() < 0.35


def wind(t):
    """Shared wind strength (always blowing left->right), 0.1..~1.9."""
    w = 0.65 + 0.35 * math.sin(t / 9.0) + 0.2 * math.sin(t / 2.7 + 1.3)
    # deterministic gusts: some 20s windows get a smooth sin^2 bump
    if gusty(int(t // GUST_PERIOD)):
        w += 0.7 * math.sin(math.pi * (t % GUST_PERIOD) / GUST_PERIOD) ** 2
    return w


def wind_travel(t0, t1):
    """Integral of wind() over [t0, t1], in closed form, so every process
    agrees on how far a leaf has blown without stepping a simulation."""
    def base(t):
        return 0.65 * t - 0.35 * 9.0 * math.cos(t / 9.0) - 0.2 * 2.7 * math.cos(t / 2.7 + 1.3)

    def bump(u):  # integral of sin^2(pi*v/P) dv over [0, u]
        return u / 2 - GUST_PERIOD / (4 * math.pi) * math.sin(2 * math.pi * u / GUST_PERIOD)

    total = base(t1) - base(t0)
    for b in range(int(t0 // GUST_PERIOD), int(t1 // GUST_PERIOD) + 1):
        if gusty(b):
            lo, hi = max(t0, b * GUST_PERIOD), min(t1, (b + 1) * GUST_PERIOD)
            if hi > lo:
                total += 0.7 * (bump(hi - b * GUST_PERIOD) - bump(lo - b * GUST_PERIOD))
    return total


SLOT = 0.5          # a leaf may leave the tree every SLOT seconds
LEAF_LIFE = 120.0   # older leaves are dropped (both panels apply the same cutoff)


def hash01(*k):
    """Deterministic pseudo-random in [0, 1) from integers: the same in every
    process, so both panels agree on where things are."""
    return (zlib.crc32(repr(k).encode()) & 0xFFFFFF) / 0x1000000


# the garden's "IN THIS HOST WE BELIEVE" sign: each toggle picks three
# different buckets and one slogan from each
YARD_SIGN = {
    "queer": [
        "trans rights are human rights", "trans women are women", "trans men are men",
        "nonbinary people are valid", "protect trans kids", "love is love",
        "queer joy is resistance", "tabs vs spaces is a false binary",
    ],
    "progressive": [
        "black lives matter", "no human is illegal", "healthcare is a human right",
        "science is real", "kindness is everything",
    ],
    "metascience": [
        "null results are results", "replication is a love language",
        "preregister your hypotheses", "effect sizes over asterisks",
        "citations are not quality", "the h-index is not your worth",
        "open data is a public good", "peer review is unpaid labor",
        "correlation is not causation", "the Matthew effect is real",
        "share your code", "p < .05 is not a personality",
    ],
    "orgs": [
        "the iron cage has a key", "isomorphism is not innovation",
        "status is not merit", "it's institutions all the way down",
        "ceremony is not efficiency", "loose coupling is a feature",
        "satisficing is enough", "routines are memory",
    ],
    "networks": [
        "weak ties carry news, strong ties carry know-how",
        "complex contagions need wide bridges", "mind the structural holes",
        "brokers see more", "closure builds trust",
        "your friends have more friends than you", "everything is embedded",
        "structure is not destiny",
        "it's cool to get sick first",  # central people catch the flu early (Christakis & Fowler 2010)
    ],
    "distinctions": [  # JARGON is not RELATED JARGON
        "status is not merit", "homophily is not influence", "centrality is not power",
        "bridging is not bonding", "legitimacy is not performance",
        "policy is not practice", "adoption is not implementation",
        "efficiency is not effectiveness", "authority is not power",
        "reliability is not validity", "precision is not accuracy",
        "significance is not importance", "prediction is not explanation",
        "robustness is not replication", "confidence is not credibility",
        "an outlier is not an error", "diversity is not inclusion",
        "sex is not gender", "gender is not sexuality",
    ],
    "counterintuitive": [  # true, and sounds wrong (contested ones left out)
        "your friends have more friends than you",
        "most people have more than the average number of legs",
        "among 23 people, two likely share a birthday",
        "a new road can slow down traffic",
        "always switch doors",
        "randomness clusters",
        "armor goes where the bullet holes aren't",
        "your classes were smaller than they felt",
        "a trend in every group can reverse overall",
        "about 30% of numbers start with 1",
        "this shuffle of cards has never existed before",
        "bananas are berries, strawberries aren't",
        "groups do what nobody wants",
        "a hen is an egg's way of making another egg",  # after Samuel Butler, 1877
    ],
}


def yard_sign():
    """The built-in buckets plus anything zen-slogans.py has grown and
    verified (~/.cache/zen/slogans.json). That file is LLM output: it's
    re-checked here as plain short text before it can reach the screen."""
    signs = {k: list(v) for k, v in YARD_SIGN.items()}
    try:
        with open(os.path.expanduser("~/.cache/zen/slogans.json")) as f:
            grown = json.load(f)
    except (OSError, ValueError):
        return signs
    safe = re.compile(r"^[A-Za-z0-9 ,.'%<>=+\-:;!?/()&]{1,48}$")
    for bucket, entries in grown.items() if isinstance(grown, dict) else ():
        for e in entries if isinstance(entries, list) else ():
            text = e.get("slogan") if isinstance(e, dict) else None
            if isinstance(text, str) and safe.match(text) and text not in signs.setdefault(bucket, []):
                signs[bucket].append(text)
    return signs


class Garden:
    """A yard at night, 1-bit and dither-shaded in braille, drawn as one scene
    across the whole window: stars, a moon (the only light), a picket fence,
    a tree, a meadow swaying in the shared wind, flowers, leaves blowing off
    the tree and behind the center pane, fireflies. One ink color (@zen-ink,
    default green). Positions are in window-wide dots so both panels agree."""
    fps = 6

    def __init__(self, s, side):
        self.s = s
        # species and season: @zen-tree / @zen-season, else picked from the
        # shared seed so both panels agree. The ink follows the season unless
        # @zen-ink is set.
        seed = int(os.environ.get("ZEN_SEED", "0") or 0)
        signs = yard_sign()
        pick = random.Random(seed)
        self.beliefs = [pick.choice(signs[b]) for b in pick.sample(sorted(signs), 3)]
        self.tree_kind = (opt("zen-tree") or
                          random.Random(seed * 7 + 1).choice(["oak", "pine", "willow", "birch"]))
        self.season = (opt("zen-season") or
                       random.Random(seed * 13 + 5).choice(["summer", "autumn", "winter"]))
        # weather, also its own axis: winter is usually snowfall but sometimes
        # clear and still; summer/autumn are clear or a light rain
        odds = {"winter": ["snow", "snow", "clear"], "autumn": ["clear", "rain"]}.get(
            self.season, ["clear", "clear", "rain"])
        self.weather = (opt("zen-weather") or
                        random.Random(seed * 17 + 3).choice(odds))
        ink = (opt("zen-ink") or
               {"summer": "green", "autumn": "yellow", "winter": "white"}.get(self.season, "green")).lower()
        self.ink = getattr(curses, f"COLOR_{ink.upper()}", curses.COLOR_GREEN)
        self.resize()

    # -- geometry and static shading ---------------------------------------

    def resize(self):
        s = self.s
        self.W, self.H = 2 * s.w, 4 * s.h
        self.ox = s.x0 * 2               # this panel's left edge, in world dots
        self.WW = s.world_w * 2          # window width, in world dots
        self.gy = int(self.H * 0.72)     # where the yard meets the fence
        self.moon = (self.WW * 0.8, self.H * 0.14, max(5.0, self.H * 0.045))
        # the tree stands in the yard, in front of the fence (which it hides)
        self.tree = (self.WW * 0.14, self.gy + int((self.H - self.gy) * 0.22))
        self.dots, self.owner, self.layer = set(), {}, "far"
        self.paint_sky()
        self.layer = "near"
        self.paint_fence()
        self.layer = "far"
        if self.season == "winter":
            self.paint_snow_ground()
        self.paint_tree()
        # mixed pixels: the fence is near (solid octants), the rest is air
        self.near = {p for p in self.dots if self.owner.get(p) == "near"}
        self.layout_sign()
        self.tables()

    def tables(self):
        """Lookup tables, NES style: what each blade, flower and particle is
        born with is worked out once per resize (or once per particle), and a
        frame only computes motion. Same numbers as computing them fresh."""
        gy, H = self.gy, self.H
        snowed = self.season == "winter"
        self.blades = []  # (x, wx, root, height, lean divisor, near)
        for x in range(self.W):
            wx = x + self.ox
            for layer, density in ((0, 0.04), (1, 0.0)) if snowed else ((0, 0.4), (1, 0.2)):
                if hash01(wx, layer, 7) > density:
                    continue
                root = gy + int((H - gy) * (0.15 + 0.85 * hash01(wx, layer, 8)))
                height = 3 + (root - gy) * 0.28 * (0.6 + 0.8 * hash01(wx, layer, 9))
                self.blades.append((x, wx, root, height * 0.6 if snowed else height,
                                    height / 0.15 if snowed else height, root > gy + (H - gy) * 0.55))
        self.stubble = []  # (x, wx, root, tall)
        for x in range(0 if snowed else self.W):
            wx = x + self.ox
            for k in range(2):
                if hash01(wx, k, 16) <= 0.18:
                    self.stubble.append((x, wx, gy + 1 + int((H - gy) * 0.55 * hash01(wx, k, 17)),
                                         1 + int(3 * hash01(wx, k, 18))))
        self.flowers = []  # (world x, root, height)
        for wx in range(0) if snowed else range(self.ox - (self.ox % 9), self.ox + self.W + 9, 9):
            if hash01(wx, 10) <= (0.4 if self.season == "summer" else 0.12):
                self.flowers.append((wx + int(hash01(wx, 11) * 8), H - 1 - int(hash01(wx, 12) * (H - gy) * 0.4),
                                     8 + int(hash01(wx, 13) * 10)))
        self.drifts = [(0.75 + 0.9 * hash01(k, 40), hash01(k, 41), hash01(k, 42), 18 + 22 * hash01(k, 43))
                       for k in range(self.WW // 4)]
        self.drops = [(hash01(i, 30), 40 + 25 * hash01(i, 31), hash01(i, 32), hash01(i, 33))
                      for i in range(self.WW * self.H // 250)]
        self.flakes, self.fallen = {}, {}  # particle number -> what it was born with

    def layout_sign(self):
        """IN THIS HOST / WE BELIEVE: ... / <user> is user, on a stake in the
        meadow of whichever panel is away from the tree. Drops slogans until
        it fits; wraps long ones."""
        s = self.s
        self.sign = None
        if (self.ox + self.W / 2 < self.WW / 2) == (self.tree[0] < self.WW / 2) or s.w < 18:
            return
        host = socket.gethostname().split(".")[0].upper()
        user = getpass.getuser()  # usernames are case-sensitive: keep it as-is
        inner = min(s.w - 6, 30)
        for n in range(len(self.beliefs), -1, -1):
            # header centered (loud=True); beliefs left-aligned, a wrapped
            # belief's continuation indented so each reads as one item
            body = [(("  " if i else "") + l, False)
                    for b in self.beliefs[:n] + [f"{user} is user"]
                    for i, l in enumerate(textwrap.wrap(b, inner - 2))]
            lines = [(f"IN THIS {host}", True), ("WE BELIEVE:", True), ("", False)] + body
            if all(len(l) <= inner for l, _ in lines) and len(lines) + 2 <= s.h - self.gy // 4 + 4:
                break
        else:
            return
        bw = max(len(l) for l, _ in lines) + 4
        bh = len(lines) + 2
        bottom = s.h - 3                      # board's bottom row; the stake goes below
        top = bottom - bh + 1
        left = (s.w - bw) // 2
        self.sign = (left, top, bw, bh, lines)

    def shade(self, wx, y, b, dots=None):
        """1-bit at world x: ink if brightness b beats the dither threshold."""
        x = round(wx) - self.ox
        dots = self.dots if dots is None else dots
        if 0 <= x < self.W and 0 <= y < self.H:
            if dots is self.dots:
                self.owner[(x, y)] = self.layer
            if b > 0.04 and b > DITHER[y % 64][(x + self.ox) % 64]:
                dots.add((x, y))
            else:
                dots.discard((x, y))

    def moonlight(self, wx, y):
        """How strongly a surface at (wx, y) faces the moon: 0..1, horizontal only."""
        mx, my, _ = self.moon
        return 0.5 + 0.5 * clamp((mx - wx) / (abs(mx - wx) + 40), -1.0, 1.0)

    def paint_sky(self):
        self.stars = []
        if self.weather == "rain":  # overcast: no moon, no stars
            return
        mx, my, mr = self.moon
        for y in range(self.gy):
            for x in range(self.W):
                wx = x + self.ox
                d = math.hypot(wx - mx, y - my)
                if d <= mr:  # the moon: bright, with a couple of soft maria
                    maria = 0.35 * math.exp(-((wx - mx + mr * 0.3) ** 2 + (y - my - mr * 0.2) ** 2) / (mr * 0.35) ** 2)
                    maria += 0.3 * math.exp(-((wx - mx - mr * 0.35) ** 2 + (y - my + mr * 0.3) ** 2) / (mr * 0.25) ** 2)
                    self.shade(wx, y, 0.97 - maria)
                else:  # halo, then stars
                    halo = 0.5 * math.exp(-((d - mr) / (mr * 0.9)) ** 2)
                    star = hash01(wx, y, 1) < 0.0025
                    self.shade(wx, y, max(halo, 1.0 if star else 0.0))
                    if star and halo < 0.04:
                        # each star blinks on its own period and phase
                        self.stars.append((x, y, 3 + 4 * hash01(wx, y, 6), hash01(y, wx, 19)))

    def paint_snow_ground(self):
        """Winter: a snow blanket over the yard -- brighter toward the front,
        with soft drifts rolling across the window -- and caps on the pickets."""
        gy, H = self.gy, self.H
        for y in range(gy, H):
            for x in range(self.W):
                wx = x + self.ox
                drift = 0.08 * math.sin(wx * 0.05 + 1.3) + 0.05 * math.sin(wx * 0.13)
                depth = (y - gy) / max(1, H - gy)
                self.shade(wx, y, 0.12 + 0.35 * depth + drift)
        top = gy - int(H * 0.08)
        self.layer = "near"  # snow caps sit on the pickets
        for wx in range(self.ox - 6, self.ox + self.W + 6):
            if wx % 6 < 2:
                self.shade(wx, top - 1, 1.0)
                self.shade(wx, top, 1.0)
        self.layer = "far"

    def paint_fence(self):
        """A low picket fence: 2-dot pickets every 6 dots, two rails."""
        gy, H = self.gy, self.H
        top = gy - int(H * 0.08)
        rails = (gy - int(H * 0.025), gy - int(H * 0.06))
        x0 = self.ox - (self.ox % 6) - 6
        for wx in range(x0, self.ox + self.W + 6):
            for ry in rails:  # rails, behind the pickets
                self.shade(wx, ry, 0.35)
            u = wx % 6
            if u < 2:  # a 2-dot picket with a point on top
                lit = self.moonlight(wx, top)
                for y in range(top + (1 - u if self.moon[0] > wx else u), gy):
                    edge = u == (1 if self.moon[0] > wx else 0)
                    self.shade(wx, y, 0.9 if edge else 0.2 + 0.5 * lit)

    # species shape: trunk length (fraction of height), branching depth,
    # fork angle range, length ratio per fork, chance of a three-way fork,
    # leaf-clump radius (fraction of height)
    TREES = {
        "oak":    (0.15, 5, (26, 44), 0.76, 0.35, 0.075),
        "birch":  (0.28, 4, (12, 22), 0.72, 0.2, 0.045),
        "willow": (0.17, 4, (34, 52), 0.74, 0.3, 0.032),
    }

    def skeleton(self, kind, extra=0):
        """Grow a branching skeleton from the trunk base. Returns segments
        (x0, y0, x1, y1, depth_left) and tips (x, y), in world dots."""
        tx, base = self.tree
        trunk, depth, (amin, amax), ratio, p3, _ = self.TREES[kind]
        segments, tips = [], []

        def grow(x, y, deg, length, d):
            th = math.radians(deg)
            x1, y1 = x + length * math.sin(th), y - length * math.cos(th)
            segments.append((x, y, x1, y1, d))
            if d == 0:
                tips.append((x1, y1))
                return
            n = 3 if hash01(round(x), round(y), 10) < p3 else 2
            for j in range(n):
                spread = amin + (amax - amin) * hash01(round(x1), round(y1), j)
                turn = (j - (n - 1) / 2) * spread * (2 if n == 2 else 1)
                grow(x1, y1, deg + turn + 10 * (hash01(j, d, round(x), 11) - 0.5),
                     length * (ratio + 0.1 * hash01(d, j, round(y), 12)), d - 1)

        grow(tx, base + 2, 0, self.H * trunk, depth + extra)
        # fit: scale about the base so the crown (tips plus their leaf clumps)
        # stays below the top margin, however tall this one grew
        top = min(y for _, y in tips) - self.H * self.TREES[kind][5]
        limit = self.H * 0.06
        if top < limit:
            k = (base - limit) / (base - top)
            fit = lambda x, y: (tx + (x - tx) * k, base + (y - base) * k)
            segments = [(*fit(x0, y0), *fit(x1, y1), d) for x0, y0, x1, y1, d in segments]
            tips = [fit(x, y) for x, y in tips]
        return segments, tips

    def paint_limbs(self, segments, pale=False):
        """Tapered limbs, shaded round: lit on the moon side, dark on the
        other. pale (birch): light bark with dark flecks."""
        side = 1 if self.moon[0] > self.tree[0] else -1
        for x0, y0, x1, y1, d in segments:
            w = 0.4 + 0.55 * d  # half-width in dots
            length = math.hypot(x1 - x0, y1 - y0)
            nx, ny = (y0 - y1) / (length + 1e-9), (x1 - x0) / (length + 1e-9)  # perpendicular
            for i in range(int(length * 2) + 1):
                t = i / (length * 2 + 1e-9)
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                if w < 1:
                    self.shade(px, round(py), 0.95)
                    continue
                for k in range(-int(w), int(w) + 1):
                    u = k / w
                    if pale:
                        fleck = hash01(round(py) // 2, d, 8) < 0.2 and hash01(k, round(py) // 2, 9) < 0.7
                        b = 0.0 if fleck else 0.6 + 0.35 * max(0.0, u * side * nx)
                    else:
                        b = 0.85 if u * side * (1 if nx >= 0 else -1) > 0.5 else 0.25 + 0.4 * max(0.0, u * side)
                    self.shade(px + k * nx, round(py + k * ny), b)

    def paint_foliage(self, clumps, crown, airy):
        """A front view of the crown: leaf clumps fill its volume (hiding the
        inner limbs), shaded twice -- the crown as one rounded mass lit from
        the moon side and above, and each clump as its own small sphere for a
        lumpy, leafy surface. clumps: (x, y, r); crown: (cx, cy, radius)."""
        side = 1 if self.moon[0] > self.tree[0] else -1
        lx, ly, lz = 0.55 * side, -0.55, 0.62
        ccx, ccy, cr = crown
        best = {}  # (x, y) -> (inside, cx, cy, r): the clump nearest its own surface
        for cx, cy, r in clumps:
            for y in range(int(cy - r) - 1, int(cy + r) + 2):
                for wx in range(int(cx - r) - 1, int(cx + r) + 2):
                    inside = 1 - math.hypot(wx - cx, y - cy) / r
                    if inside > -0.15 and inside > best.get((wx, y), (-9,))[0]:
                        best[(wx, y)] = (inside, cx, cy, r)
        for (wx, y), (inside, cx, cy, r) in best.items():
            if inside <= -0.15 * hash01(wx, y, 5):  # ragged, leafy edges
                continue
            nx, ny = (wx - cx) / r, (y - cy) / r
            local = max(0.0, nx * lx + ny * ly + math.sqrt(max(0.0, 1 - nx * nx - ny * ny)) * lz)
            gx, gy = clamp((wx - ccx) / cr, -1.0, 1.0), clamp((y - ccy) / cr, -1.0, 1.0)
            mass = max(0.0, gx * lx + gy * ly + math.sqrt(max(0.0, 1 - gx * gx - gy * gy)) * lz)
            self.shade(wx, y, (0.06 + 0.85 * local * (0.35 + 0.65 * mass)) * (1 - airy))

    def paint_tree(self):
        """One tree, grown from a branching skeleton: oak (wide, low), birch
        (narrow, upright, pale bark), willow (strands trail from its tips),
        pine (dithered tiers). Leaves clump on the branch tips; in autumn
        they thin out, in winter deciduous trees are bare twigs and it snows."""
        tx, base = self.tree
        H = self.H
        kind, winter = self.tree_kind, self.season == "winter"
        self.crown_at, self.willow_tips = None, []

        if kind == "pine":
            self.paint_pine()
            return

        segments, tips = self.skeleton(kind, extra=1 if winter else 0)
        cx = sum(x for x, _ in tips) / len(tips)
        cy = sum(y for _, y in tips) / len(tips)
        spread = max(math.hypot(x - cx, y - cy) for x, y in tips)
        if not winter:
            self.crown_at = (cx, cy, spread * 0.8)
        if not (self.ox - spread * 2 < tx < self.ox + self.W + spread * 2):
            if kind == "willow" and not winter:
                self.willow_tips = tips
            return

        self.paint_limbs(segments, pale=kind == "birch")
        if winter:  # bare, and still: winter's motion is the snow
            return
        airy = 0.3 if self.season == "autumn" else 0.0
        _, depth, _, _, _, r = self.TREES[kind]
        r *= H
        # clumps along every branch past the first forks, plus the tips, so
        # the crown is a filled volume rather than a ring around bare limbs
        clumps = [(x, y, r) for x, y in tips]
        for x0, y0, x1, y1, d in segments:
            if d <= depth - 2:
                n = max(1, int(math.hypot(x1 - x0, y1 - y0) / (r * 0.8)))
                for i in range(1, n + 1):
                    clumps.append((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, r * 1.1))
        self.paint_foliage(clumps, (cx, cy, spread + r), airy)
        if kind == "willow":
            self.willow_tips = tips

    def paint_pine(self):
        tx, base = self.tree
        H = self.H
        self.paint_limbs([(tx, base + 2, tx, base - H * 0.12, 3)])
        apex, side = base - H * 0.62, (1 if self.moon[0] > tx else -1)
        for i in range(5):  # overlapping tiers with drooping, jagged hems
            top = apex + i * H * 0.1
            bottom = top + H * 0.17
            spread = H * (0.05 + 0.04 * i)
            for wx in range(int(tx - spread) - 1, int(tx + spread) + 2):
                u = (wx - tx) / spread
                if abs(u) > 1:
                    continue
                hem = bottom - abs(u) * H * 0.03 + 2 * hash01(wx, i, 6)  # tips droop
                rise = top + abs(u) * (bottom - top) * 0.85              # sloped shoulders
                for y in range(int(rise), int(hem) + 1):
                    edge = y >= int(hem) - 1 or y <= int(rise) + 1
                    self.shade(wx, y, 0.85 if edge and u * side > -0.3 else
                               0.12 + 0.6 * max(0.0, 0.7 * u * side + 0.3) * (1 - (y - rise) / (hem - rise + 1) * 0.5))

    def strands(self, now, wd, dots):
        """Willow: strands hanging from the branch tips, swaying with the wind."""
        base = self.tree[1]
        for i, (tx, ty) in enumerate(self.willow_tips):
            for off in (0,):
                length = (base - ty) * (0.5 + 0.4 * hash01(i, off, 13))
                sway = (wd * 1.8 + 0.8 * math.sin(now * 1.2 + i * 0.7)) * 3
                for k in range(int(length)):
                    if k % 4 == 3 or (self.season == "autumn" and hash01(i, off, k, 14) < 0.35):
                        continue  # leafy, broken strands; balder in autumn
                    f = k / max(1, length)
                    x = round(tx + off + sway * f * f) - self.ox
                    if 0 <= x < self.W:
                        dots.add((x, round(ty + k)))

    def spindrift(self, now, wd, dots):
        """Winter: snow skimming across the ground, blowing right and behind
        the center pane. More of it the windier it is: each particle only
        shows above its own wind threshold, so gusts kick up streams."""
        gy, H = self.gy, self.H
        span = self.WW + 40
        # distance the wind has carried things so far (wind_travel's smooth part)
        travel = 0.65 * now - 3.15 * math.cos(now / 9.0) - 0.54 * math.cos(now / 2.7 + 1.3)
        for k, (thresh, depth, h0, speed) in enumerate(self.drifts):
            if wd < thresh:
                continue
            y = gy + 1 + int((H - gy - 2) * depth) - round(abs(math.sin(now * 3 + k)) * 2)
            x = (h0 * span + travel * speed) % span - 20 - self.ox
            for i in range(1 + int(2 * depth)):  # nearer flakes streak longer
                px = round(x) - i
                if 0 <= px < self.W:
                    dots.add((px, y))

    def rain(self, now, wd, dots):
        """Light rain: short streaks slanting with the wind, looping down the
        window, and little splash ticks flickering in the grass."""
        slant = 0.25 + 0.35 * wd
        for h30, speed, h32, h33 in self.drops:
            wx0 = h30 * (self.WW + self.H * slant) - self.H * slant
            y = (now * speed + h32 * (self.H + 20)) % (self.H + 20) - 10
            for k in range(3):
                x = round(wx0 + slant * (y - k)) - self.ox
                if 0 <= x < self.W and 0 <= y - k < self.gy + (self.H - self.gy) * h33:
                    dots.add((x, round(y - k)))
        tick = int(now * 8)
        for i in range(self.W // 6):
            x = int(hash01(i, tick, 34) * self.W)
            y = self.gy + int(hash01(i, tick, 35) * (self.H - self.gy))
            dots.add((x, y))

    def snow(self, now, dots):
        """Winter: flakes across the whole window, drifting with the wind."""
        first = int((now - 60) // 0.15)
        for k in [k for k in self.flakes if k < first]:
            del self.flakes[k]
        for k in range(first, int(now // 0.15) + 1):
            t0 = k * 0.15
            if k not in self.flakes:
                r = random.Random(k * 31 + 7)
                self.flakes[k] = (r.uniform(-self.WW * 0.3, self.WW), r.uniform(3, 7), 5.0 * r.uniform(0.6, 1.2))
            x0, vy, drift = self.flakes[k]
            y = vy * (now - t0)
            if y >= self.H:
                continue
            x = x0 + drift * wind_travel(t0, now) + 2 * math.sin(now * 1.5 + k)
            px = round(x) - self.ox
            if 0 <= px < self.W:
                dots.add((px, round(y)))


    # -- per frame -----------------------------------------------------------

    def leaves(self, now):
        """Leaves leaving the tree, blown by the shared wind: (world_x, y)."""
        if not self.crown_at:
            return
        tx, cy, cr = self.crown_at
        first = int((now - LEAF_LIFE) // SLOT)
        for k in [k for k in self.fallen if k < first]:
            del self.fallen[k]
        for k in range(first, int(now // SLOT) + 1):
            t0 = k * SLOT
            if t0 > now:
                continue
            if k not in self.fallen:  # None: no leaf left the tree in this slot
                r = random.Random(k)
                self.fallen[k] = None if r.random() > (0.8 if self.season == "autumn" else 0.3) * wind(t0) else (
                    tx + r.uniform(-cr, cr), cy + r.uniform(-cr * 0.5, cr * 0.5),
                    r.uniform(0.6, 1.2), r.uniform(1.5, 4.0), r.uniform(0, 6.28))
            if self.fallen[k] is None:
                continue
            x0, y0, speed, vy, phase = self.fallen[k]
            x = x0 + 12.0 * speed * wind_travel(t0, now)
            y = y0 + vy * (now - t0) + (2.0 / 1.7) * (math.cos(1.7 * t0 + phase) - math.cos(1.7 * now + phase))
            if x < self.WW and y < self.H - 1:
                yield x, y, int(now * 4 + phase) % 2

    def frame(self, now):
        s, H, gy = self.s, self.H, self.gy
        dots, near = set(self.dots), set(self.near)  # near: also in dots
        wd = wind(now)

        # twinkle: each star goes out briefly, on its own period and phase
        for x, y, period, phase in self.stars:
            if (now / period + phase) % 1 < 0.2 / period:
                dots.discard((x, y))

        # meadow: blades rooted at different depths; nearer ones taller, all
        # leaning with the wind and a wave that rolls across the window. In
        # winter: just a few dead stalks poking through the snow, stiff,
        # barely trembling.
        for x, wx, root, height, lean_div, front in self.blades:
            lean = (wd * 1.4 + 0.6 * math.sin(now * 1.9 + wx * 0.07)) / lean_div
            for i in range(int(height)):
                px = x + round(lean * i * i / 2)
                if 0 <= px < self.W:
                    dots.add((px, root - i))
                    if front:
                        near.add((px, root - i))

        # stubble: tiny tufts scattered through the back of the yard, each at its
        # own depth (no layers), so the space behind the tall grass isn't bare
        for x, wx, root, tall in self.stubble:
            bend = 1 if wd + 0.5 * math.sin(now * 1.9 + wx * 0.07) > 1.1 else 0
            for i in range(tall):
                dots.add((x + (bend if i == tall - 1 else 0), root - i))

        winter, summer = self.season == "winter", self.season == "summer"
        if winter:
            self.spindrift(now, wd, dots)
        if self.tree_kind == "willow" and not winter:
            self.strands(now, wd, dots)
        if self.weather == "snow":
            self.snow(now, dots)
        elif self.weather == "rain":
            self.rain(now, wd, dots)

        # flowers: stems with round heads, nodding in the wind (a few late
        # ones in autumn, none in winter)
        for fx, root, height in self.flowers:
            lean = (wd + 0.3 * math.sin(now * 1.3 + fx)) * 0.08
            flower = {(fx - self.ox + round(lean * i * i / 4), root - i) for i in range(height)}
            hx, hy = fx - self.ox + round(lean * height * height / 4), root - height - 1
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx * dx + dy * dy <= 4 and (dx, dy) != (0, 0):
                        flower.add((hx + dx, hy + dy))
            dots |= flower
            near |= flower
            dots.discard((hx, hy))  # the flower's center
            near.discard((hx, hy))

        # leaves: little two-dot flecks, tumbling
        for lx, ly, flip in self.leaves(now):
            x, y = round(lx) - self.ox, round(ly)
            dots.add((x, y))
            dots.add((x + 1, y + (1 if flip else -1)))

        # fireflies: drifting near the grass, blinking (summer things)
        for k in range(max(3, self.WW // 60) if summer and self.weather != "rain" else 0):
            fx = (hash01(k, 20) * self.WW + 18 * math.sin(now * 0.3 + k) + 9 * math.sin(now * 0.71 + 2 * k)) % self.WW
            fy = gy - 6 + (H - gy) * 0.5 * hash01(k, 21) + 6 * math.sin(now * 0.5 + 3 * k)
            if math.sin(now * (1.3 + hash01(k, 22)) + k * 5) > 0.55:
                x, y = round(fx) - self.ox, round(fy)
                for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    dots.add((x + dx, y + dy))

        if self.sign:  # the board blocks what's behind it; outline and stake in dots
            left, top, bw, bh, lines = self.sign
            x0, x1, y0, y1 = left * 2, (left + bw) * 2 - 1, top * 4, (top + bh) * 4 - 1
            stake = range(y1 + 1, H)
            for x, y in list(dots):
                if (x0 <= x <= x1 and y0 <= y <= y1) or (abs(x - (x0 + x1) // 2) <= 1 and y in stake):
                    dots.discard((x, y))
                    near.discard((x, y))
            board = {(x, y) for x in range(x0, x1 + 1) for y in (y0 + 1, y1 - 1)}
            board |= {(x, y) for y in range(y0 + 1, y1) for x in (x0, x1)}
            board |= {((x0 + x1) // 2, y) for y in stake}
            dots |= board
            near |= board

        draw_cells(s, dots, near, self.W, H, self.ink)

        if self.sign:
            left, top, bw, bh, lines = self.sign
            for i, (line, loud) in enumerate(lines):
                x = left + (bw - len(line)) // 2 if loud else left + 2
                s.put(top + 1 + i, x, line, self.ink, curses.A_BOLD if loud else 0)



# ---------------------------------------------------------------- coffee

# printed on the mug; USER / HOST are filled in (bold red). Tried in order
# until one fits the mug.
MUG_SLOGANS = [
    ["don't talk to", "USER", "until i've had my morning", "HOST"],
    ["don't talk to", "USER", "until i've had", "my morning", "HOST"],
    ["HOST"],
]
COLD_AFTER = 45 * 60  # the coffee stops steaming after 45 minutes


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Coffee:
    """A desk at night, 1-bit and dither-shaded in braille (think Obra Dinn,
    not ASCII art). One panel has a mug (with the hostname printed on a
    label), the other a banker's lamp under a wall clock. The lamp is the
    only light: the wall, table, mug and saucer are shaded by distance and
    direction to its bulb, across both panels. Everything is one ink color
    (@zen-ink, default yellow). ZEN_SEED, shared by both spacers, picks which
    side gets the mug.

    Static shading is computed once per resize; each frame adds the moving
    bits (steam, pull chain, clock hands)."""
    fps = 8

    def __init__(self, s, side):
        self.s = s
        seed = int(os.environ.get("ZEN_SEED", "0") or 0)
        self.mug_side = "left" if seed % 2 == 0 else "right"
        self.mug = side == self.mug_side
        self.name = " ".join(socket.gethostname().split(".")[0].upper())
        self.user = " ".join(getpass.getuser().upper())
        ink = (opt("zen-ink") or "yellow").lower()
        self.ink = getattr(curses, f"COLOR_{ink.upper()}", curses.COLOR_YELLOW)
        self.rng = random.Random()
        self.start = time.time()
        self.steam = []  # (born, x0, y0, phase), in dots
        self.resize()

    # -- geometry and static shading ---------------------------------------

    def resize(self):
        s = self.s
        h, w = s.h, s.w
        self.W, self.H = 2 * w, 4 * h
        self.table_y = h - 4 if h >= 14 else h - 1
        self.cx = w // 2
        widest = max(len(l) for l in self.slogan(MUG_SLOGANS[0])) + 6
        self.mw = clamp(widest, len(self.name) + 4, max(10, w - 6))
        self.mh = max(7, round(self.mw * 0.45))
        self.sw = clamp(w * 3 // 5, 15, 35) | 1
        self.clock_cols = clamp(w * 2 // 5, 0, 24) // 2 * 2
        self.lh = clamp(h * 9 // 20, 10, max(10, self.table_y - self.clock_cols // 2 - 4))

        # the bulb, in this panel's dot coordinates; the lamp panel is assumed
        # to be this one's mirror image across the center pane
        lamp_x0 = s.x0 if not self.mug else (s.world_w - w if self.mug_side == "left" else 0)
        self.shade_top = max(1, self.table_y - self.lh) * 4
        self.bulb = ((lamp_x0 + w // 2) * 2 + 1 - s.x0 * 2, self.shade_top + 12)

        self.dots = set()
        self.paint_room()
        if self.mug:
            self.paint_mug()
        else:
            self.paint_lamp()

    def light(self, x, y):
        """Lamp light reaching (x, y): falls off with distance, strong in the
        cone under the shade, faint above it."""
        bx, by = self.bulb
        d = math.hypot(x - bx, y - by)
        cone = clamp(((y - by) / (d + 1e-9) - 0.25) / 0.5, 0.0, 1.0) if y > by else 0.12
        return cone / (1 + (d / 45) ** 2) + 0.9 * math.exp(-(d / 7) ** 2)

    def shade(self, x, y, b):
        """1-bit: the dot is ink if brightness b beats the dither threshold.
        Below a small floor nothing is drawn, so falloff tails don't leave a
        lattice of lone dots."""
        if 0 <= x < self.W and 0 <= y < self.H:
            if b > 0.04 and b > DITHER[y % 64][x % 64]:
                self.dots.add((x, y))
            else:
                self.dots.discard((x, y))

    def paint_room(self):
        top = self.table_y * 4
        for y in range(self.H):
            for x in range(self.W):
                if y < top:  # wall: dark, lit only near the lamp (a low ambient
                    # level would show the dither matrix as a dot lattice)
                    self.shade(x, y, 0.4 * self.light(x, y))
                elif y == top:  # the table's edge catches the light
                    self.shade(x, y, 0.35 + 0.65 * self.light(x, y))
                else:  # table top, darker toward the front
                    depth = (y - top) / max(1, self.H - top)
                    self.shade(x, y, 0.8 * self.light(x, top) * (1 - 0.7 * depth))

    def paint_lamp(self):
        bx, by = self.bulb
        half, top = self.sw, self.shade_top
        bottom = top + 12
        # shade: a glass dome, glowing toward its lit bottom edge
        for x in range(-half, half + 1):
            crown = top + round(12 * 0.55 * (x / half) ** 2)
            for y in range(crown, bottom + 1):
                t = (y - crown) / max(1, bottom - crown)
                edge = y == crown or y == bottom
                self.shade(bx + x, y, 0.95 if edge else 0.18 + 0.6 * t * t)
        floor = self.table_y * 4
        # base: a brass dome lit from above
        bhalf, bh = max(6, half * 3 // 5), 6
        for x in range(-bhalf, bhalf + 1):
            u = x / bhalf
            rim = floor - round(bh * math.sqrt(max(0.0, 1 - u * u)))
            for y in range(rim, floor):
                self.shade(bx + x, y, 0.25 + 0.7 * (1 - u * u) * (1 - (y - rim) / (bh + 1)))
        # stem
        for y in range(bottom + 1, floor - bh):
            self.shade(bx, y, 1.0)
            self.shade(bx + 1, y, 0.0)
        # clock face: a dark disc on the wall with a lit rim and ticks
        cw = self.clock_cols
        if cw >= 8:
            r = cw - 1
            ccx, ccy = (self.cx - cw // 2) * 2 + cw, 4 + cw
            self.clock_center = (ccx, ccy, r)
            for y in range(ccy - r - 1, ccy + r + 2):
                for x in range(ccx - r - 1, ccx + r + 2):
                    if math.hypot(x - ccx, y - ccy) <= r + 0.5:
                        self.shade(x, y, 0.0)
            for i in range(360):
                th = math.radians(i)
                self.shade(round(ccx + r * math.sin(th)), round(ccy - r * math.cos(th)), 1.0)
            for hour in range(12):
                self.line(ccx, ccy, hour * 30, r * (0.72 if hour % 3 == 0 else 0.84), r - 1, self.dots)
        else:
            self.clock_center = None

    def paint_mug(self):
        bx, by = self.bulb
        handle_cols = max(5, self.mh * 2 // 3)
        mx = self.cx - (self.mw + handle_cols) // 2  # center mug + handle together
        self.mx = mx
        xl, xr = mx * 2, (mx + self.mw) * 2
        xc, hw = (xl + xr) / 2, (xr - xl) / 2
        top_row = self.table_y - self.mh
        self.top_row = top_row
        yt, yb, e = top_row * 4 + 3, self.table_y * 4 - 3, 3.5
        side = 1 if bx > xc else -1  # which way the lamp is
        lx, lz = 0.8 * side, 0.6
        # it's a dim room; give the mug enough fill to read as a form
        strength = clamp(self.light(xc, (yt + yb) / 2) * 2.2, 0.6, 1.0)

        # saucer: a flat ellipse on the table, lit on top, bright rim
        sa, sb, scy = hw + 12, 3.0, self.table_y * 4 + 1
        for y in range(int(scy - sb) - 1, int(scy + sb) + 2):
            for x in range(int(xc - sa) - 1, int(xc + sa) + 2):
                v = ((x - xc) / sa) ** 2 + ((y - scy) / sb) ** 2
                if v <= 1:
                    self.shade(x, y, 0.95 if v > 0.75 and y <= scy else 0.15 + 0.4 * strength)

        # handle: a ring on the right, shaded by which way its surface faces,
        # with a lit edge so it reads even when the lamp is on the far side
        hcy, ro = (yt + yb) / 2, (yb - yt) * 0.24
        hcx, ri = xr + ro * 0.5, ro * 0.55
        for y in range(int(hcy - ro) - 1, int(hcy + ro) + 2):
            for x in range(xr, int(hcx + ro) + 2):
                d = math.hypot(x - hcx, y - hcy)
                if ri <= d <= ro:
                    nx = (x - hcx) / (d + 1e-9)
                    edge = d >= ro - 1 or d <= ri + 1
                    self.shade(x, y, 0.85 if edge else 0.12 + 0.75 * strength * max(0.0, nx * lx + 0.45))

        # body: a lit cylinder, with a curved bottom
        for x in range(xl, xr + 1):
            u = clamp((x - xc) / hw, -1.0, 1.0)
            nz = math.sqrt(1 - u * u)
            lambert = max(0.0, u * lx + nz * lz)
            bottom = yb + e * nz
            for y in range(yt, int(bottom) + 1):
                # silhouette: the sides and the bottom curve catch a rim of light
                edge = x <= xl + 1 or x >= xr - 1 or y >= int(bottom) - 1
                self.shade(x, y, 0.9 if edge else 0.1 + 0.85 * strength * lambert)

        # rim and coffee: the opening as an ellipse, dark coffee inside with a
        # glint on the lamp side
        for y in range(int(yt - e) - 1, int(yt + e) + 2):
            for x in range(xl - 1, xr + 2):
                v = ((x - xc) / hw) ** 2 + ((y - yt) / e) ** 2
                if v <= 1.08:
                    glint = math.exp(-(((x - xc - side * hw * 0.45) / (hw * 0.18)) ** 2 + ((y - yt) / 1.5) ** 2))
                    self.shade(x, y, 1.0 if v > 0.8 else 0.04 + 0.8 * glint)

        # the printed label: a clear decal, so the mug shows between words
        for slogan in MUG_SLOGANS:
            lines = self.slogan(slogan)
            if max(map(len, lines)) <= self.mw - 4 and len(lines) <= self.mh - 4:
                break
        self.label = (slogan, lines)
        self.label_y = top_row + 2 + (self.mh - 3 - len(lines)) // 2

    # -- helpers -------------------------------------------------------------

    def slogan(self, lines):
        return [self.user if l == "USER" else self.name if l == "HOST" else l for l in lines]

    @staticmethod
    def line(cx, cy, deg, r0, r1, dots):
        th = math.radians(deg)
        steps = int((r1 - r0) * 2) + 1
        for i in range(steps + 1):
            t = r0 + (r1 - r0) * i / steps
            dots.add((round(cx + t * math.sin(th)), round(cy - t * math.cos(th))))

    # -- per frame -----------------------------------------------------------

    def frame(self, now):
        s = self.s
        dots = set(self.dots)
        if self.mug:
            self.frame_steam(now, dots)
        else:
            self.frame_lamp(now, dots)

        cells = {}
        for x, y in dots:
            if 0 <= x < self.W and 0 <= y < self.H:
                key = (y // 4, x // 2)
                cells[key] = cells.get(key, 0) | Braille.BIT[(x % 2, y % 4)]
        for (row, col), bits in cells.items():
            s.put(row, col, pix(bits), self.ink)

        if self.mug:  # the printed label, as real text
            slogan, lines = self.label
            for i, (line, raw) in enumerate(zip(lines, slogan)):
                loud = raw in ("USER", "HOST")
                x0 = self.mx + (self.mw - len(line)) // 2
                if loud:  # spaced-out names keep their gaps dark, to stay legible
                    s.put(self.label_y + i, x0, line, self.ink, curses.A_BOLD)
                else:  # clear decal: ink only where there are letters
                    for j, ch in enumerate(line):
                        if ch != " ":
                            s.put(self.label_y + i, x0 + j, ch, self.ink)

    def frame_steam(self, now, dots):
        """Steam: soft puffs that grow, drift and thin out, dithered so they
        stipple away as they rise."""
        warmth = max(0.0, 1 - (now - self.start) / COLD_AFTER)
        xl = self.mx * 2
        if self.rng.random() < 0.9 * warmth:
            self.steam.append((now, xl + self.rng.uniform(6, self.mw * 2 - 6),
                               self.top_row * 4 - 2, self.rng.uniform(0, 6.28)))
        life = 5.0
        self.steam = [p for p in self.steam if now - p[0] < life]
        for born, x0, y0, phase in self.steam:
            age = now - born
            x = x0 + 4 * math.sin(age * 1.3 + phase) + 1.2 * age
            y = y0 - 7 * age
            r = 1.5 + 1.6 * age
            peak = 0.75 * (1 - age / life)
            for py in range(int(y - r), int(y + r) + 1):
                for px in range(int(x - r), int(x + r) + 1):
                    d2 = ((px - x) ** 2 + (py - y) ** 2) / (r * r)
                    if d2 < 1 and 0 <= px < self.W and 0 <= py < self.H and peak * (1 - d2) > DITHER[py % 64][px % 64]:
                        dots.add((px, py))

    def frame_lamp(self, now, dots):
        bx, by = self.bulb
        # pull chain: a pendulum from the shade's edge
        px, py = bx + self.sw * 3 // 5, by + 1
        length = max(8, (self.table_y * 4 - by) // 3)
        swing = 0.22 * math.sin(now * 1.1)
        for t in range(length + 1):
            q = (round(px + t * math.sin(swing)), round(py + t * math.cos(swing)))
            if t % 2 == 0:
                dots.add(q)
            else:
                dots.discard(q)
        ex, ey = round(px + length * math.sin(swing)), round(py + length * math.cos(swing))
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            dots.add((ex + dx, ey + dy))
        # clock hands, on local time
        if self.clock_center:
            ccx, ccy, r = self.clock_center
            lt = time.localtime(now)
            self.line(ccx, ccy, 6 * lt.tm_min, 0, r * 0.8, dots)
            self.line(ccx, ccy, 30 * (lt.tm_hour % 12) + lt.tm_min / 2, 0, r * 0.5, dots)


def bayer(n):
    """n x n ordered-dither thresholds in (0, 1)."""
    m = [[0]]
    while len(m) < n:
        k = len(m)
        m = [[4 * m[y % k][x % k] + (0, 2, 3, 1)[(y // k) * 2 + x // k] for x in range(2 * k)] for y in range(2 * k)]
    return [[(v + 0.5) / (n * n) for v in row] for row in m]


# Bayer thresholds jittered with a little fixed noise: keeps the ordered
# look in the midtones but breaks up the grid pattern in the shadows
_noise = random.Random(4242)
DITHER = [[0.75 * bayer(8)[y % 8][x % 8] + 0.25 * _noise.random() for x in range(64)] for y in range(64)]


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]  # 4x4 ordered dither


# Unicode 16 octants (2x4 solid blocks), indexed by the same bits as braille.
# 230 live in U+1CD00..; the other 26 patterns are older block elements.
# Generated from unicodedata 17 so older pythons need no octant names.
OCTANTS = (
    " \U0001cea8\U0001cd00\u2598\U0001cd09\U0001cd0a\U0001fbe6\U0001cd0d\U0001ceab\U0001fb82\U0001cd01\U0001cd02\U0001cd0b\U0001cd0c\U0001cd0e\U0001cd0f\U0001cd03\U0001cd04\U0001cd06\U0001cd07\U0001cd10\U0001cd11\U0001cd14\U0001cd15\u259d\U0001cd05\U0001cd08\u2580\U0001cd12\U0001cd13\U0001cd16\U0001cd17"
    "\U0001cd18\U0001cd19\U0001cd1c\U0001cd1d\U0001cd27\U0001cd28\U0001cd2b\U0001cd2c\U0001cd1a\U0001cd1b\U0001cd1e\U0001cd1f\U0001cd29\U0001cd2a\U0001cd2d\U0001cd2e\U0001fbe7\U0001cd20\U0001cd23\U0001cd24\U0001cd2f\U0001cd30\U0001cd33\U0001cd34\U0001cd21\U0001cd22\U0001cd25\U0001cd26\U0001cd31\U0001cd32\U0001cd35\U0001fb85"
    "\U0001cea3\U0001cd36\U0001cd39\U0001cd3a\u2596\U0001cd45\U0001cd48\u258c\U0001cd37\U0001cd38\U0001cd3b\U0001cd3c\U0001cd46\U0001cd47\U0001cd49\U0001cd4a\U0001cd3d\U0001cd3e\U0001cd41\U0001cd42\U0001cd4b\U0001cd4c\U0001cd4e\U0001cd4f\U0001cd3f\U0001cd40\U0001cd43\U0001cd44\u259e\U0001cd4d\U0001cd50\u259b"
    "\U0001cd51\U0001cd52\U0001cd55\U0001cd56\U0001cd61\U0001cd62\U0001cd65\U0001cd66\U0001cd53\U0001cd54\U0001cd57\U0001cd58\U0001cd63\U0001cd64\U0001cd67\U0001cd68\U0001cd59\U0001cd5a\U0001cd5d\U0001cd5e\U0001cd69\U0001cd6a\U0001cd6d\U0001cd6e\U0001cd5b\U0001cd5c\U0001cd5f\U0001cd60\U0001cd6b\U0001cd6c\U0001cd6f\U0001cd70"
    "\U0001cea0\U0001cd71\U0001cd74\U0001cd75\U0001cd80\U0001cd81\U0001cd84\U0001cd85\U0001cd72\U0001cd73\U0001cd76\U0001cd77\U0001cd82\U0001cd83\U0001cd86\U0001cd87\U0001cd78\U0001cd79\U0001cd7c\U0001cd7d\U0001cd88\U0001cd89\U0001cd8c\U0001cd8d\U0001cd7a\U0001cd7b\U0001cd7e\U0001cd7f\U0001cd8a\U0001cd8b\U0001cd8e\U0001cd8f"
    "\u2597\U0001cd90\U0001cd93\u259a\U0001cd9c\U0001cd9d\U0001cda0\U0001cda1\U0001cd91\U0001cd92\U0001cd94\U0001cd95\U0001cd9e\U0001cd9f\U0001cda2\U0001cda3\U0001cd96\U0001cd97\U0001cd99\U0001cd9a\U0001cda4\U0001cda5\U0001cda8\U0001cda9\u2590\U0001cd98\U0001cd9b\u259c\U0001cda6\U0001cda7\U0001cdaa\U0001cdab"
    "\u2582\U0001cdac\U0001cdaf\U0001cdb0\U0001cdbb\U0001cdbc\U0001cdbf\U0001cdc0\U0001cdad\U0001cdae\U0001cdb1\U0001cdb2\U0001cdbd\U0001cdbe\U0001cdc1\U0001cdc2\U0001cdb3\U0001cdb4\U0001cdb7\U0001cdb8\U0001cdc3\U0001cdc4\U0001cdc7\U0001cdc8\U0001cdb5\U0001cdb6\U0001cdb9\U0001cdba\U0001cdc5\U0001cdc6\U0001cdc9\U0001cdca"
    "\U0001cdcb\U0001cdcc\U0001cdcf\U0001cdd0\u2584\U0001cddb\U0001cdde\u2599\U0001cdcd\U0001cdce\U0001cdd1\U0001cdd2\U0001cddc\U0001cddd\U0001cddf\U0001cde0\U0001cdd3\U0001cdd4\U0001cdd7\U0001cdd8\U0001cde1\U0001cde2\u2586\U0001cde4\U0001cdd5\U0001cdd6\U0001cdd9\U0001cdda\u259f\U0001cde3\U0001cde5\u2588"
)

PIXELS = "braille"  # @zen-pixels: braille, octant, or mixed (near things solid)


def pix(bits, near=False):
    """One 2x4 cell of dots as a character: braille, or solid octants."""
    if PIXELS == "octant" or (near and PIXELS == "mixed"):
        return OCTANTS[bits]
    return chr(0x2800 + bits)


def draw_cells(s, dots, near, w, h, color):
    """Dots to characters. In mixed mode a cell holding any near dot is drawn
    solid from its near dots only: the near thing hides what's behind it."""
    cells, front = {}, {}
    for x, y in dots:
        if 0 <= x < w and 0 <= y < h:
            key = (y // 4, x // 2)
            cells[key] = cells.get(key, 0) | Braille.BIT[(x % 2, y % 4)]
    if PIXELS == "mixed":
        for x, y in near:
            if 0 <= x < w and 0 <= y < h:
                key = (y // 4, x // 2)
                front[key] = front.get(key, 0) | Braille.BIT[(x % 2, y % 4)]
    for key, bits in cells.items():
        if key in front:
            s.put(*key, pix(front[key], near=True), color)
        else:
            s.put(*key, pix(bits), color)


class Braille:
    """A dot canvas over the whole pane, rendered as braille cells (2x4 dots
    each). Each dot carries a style and a rank; a cell takes the style of its
    highest-ranked dot."""
    BIT = {(0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08,
           (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80}

    def __init__(self):
        self.cells = {}  # (row, col) -> [bits, rank, style]

    def dot(self, x, y, style, rank=0):
        if x < 0 or y < 0:
            return
        c = self.cells.setdefault((y // 4, x // 2), [0, -1, style])
        c[0] |= self.BIT[(x % 2, y % 4)]
        if rank > c[1]:
            c[1], c[2] = rank, style

    def render(self, s):
        for (row, col), (bits, _, (color, attr)) in self.cells.items():
            s.put(row, col, pix(bits), color, attr)



# ---------------------------------------------------------------- ink

def brush(dots, pts, width, seed, fray=0.0, reveal=1.0):
    """Lay a brush stroke along pts (dot coordinates) into dots. width(t)
    gives the stroke's width in dots at t (0..1 along it). Dry brush: the
    width is split into bristles, each running out of ink at its own point:
    fray 0 inks every bristle to the end, toward 1 they give out earlier and
    skip, so the stroke breaks into streaks (feibai, "flying white").
    reveal < 1 draws only the start, for a stroke being painted."""
    seg = [math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:])]
    total = sum(seg) or 1.0
    bristles = 6
    runout = [1 - fray * hash01(seed, b, 1) for b in range(bristles)]
    s = 0.0
    for (x0, y0), (x1, y1), n in zip(pts, pts[1:], seg):
        if n == 0:
            continue
        nx, ny = -(y1 - y0) / n, (x1 - x0) / n
        for i in range(max(1, int(n * 2))):
            t = (s + n * i / max(1, int(n * 2))) / total
            if t > reveal:
                return
            x, y = x0 + (x1 - x0) * i / max(1, int(n * 2)), y0 + (y1 - y0) * i / max(1, int(n * 2))
            w = width(t)
            steps = max(1, int(w * 2))
            for j in range(steps + 1):
                v = j / steps - 0.5                       # -0.5..0.5 across
                b = min(bristles - 1, int((v + 0.5) * bristles))
                if t > runout[b] or (fray and hash01(seed, b, int(t * 24)) < 0.35 * fray):
                    continue
                dots.add((round(x + v * w * nx), round(y + v * w * ny)))
        s += n


def curl_path(cx, cy, r_out, turns, rot, tail, lean, ay=1.0, steps_per_turn=40):
    """A cloud curl: a log spiral wound tight at the head (centre) opening out
    to radius r_out, then a tail streaming off at angle lean (radians), in dot
    coordinates (y scaled by 1/ay so it looks round in tall cells). From the
    head outward."""
    big = 2 * math.pi * turns
    k = math.log(1 / 0.12) / big                        # inner radius 12% of outer
    pts = []
    for i in range(int(turns * steps_per_turn) + 1):
        th = big * i / (turns * steps_per_turn)
        r = r_out * math.exp(-k * (big - th))
        pts.append((cx + r * math.cos(th + rot), cy - r * math.sin(th + rot) / ay))
    # the tail leaves the outer end along its tangent and eases toward lean
    x, y = pts[-1]
    (px, py) = pts[-2]
    ang = math.atan2(-(y - py) * ay, x - px)
    for i in range(int(tail)):
        ang += (lean - ang) * 0.1 + 0.03 * math.sin(i * 0.17 + cx * 0.05)
        x, y = x + math.cos(ang), y - math.sin(ang) / ay
        pts.append((x, y))
    return pts


class Ink:
    """Shan shui, in light ink on the dark ground (a stone rubbing more than a
    scroll): mountain ridges in layers, each inked at its crest and fading
    down into blank mist, the nearer ones darker; cloud curls drifting on the
    shared wind, winding as they go, painted on as they appear and drying to
    streaks before they dissolve; a red seal in the corner."""
    fps = 6
    LIFE = 50.0     # seconds a curl lives
    SLOT = 3.0      # a curl may be born every SLOT seconds

    def __init__(self, s, side):
        self.s, self.side = s, side
        self.seed = int(os.environ.get("ZEN_SEED", "0"))
        ink = (opt("zen-ink") or "white").lower()
        self.ink = getattr(curses, f"COLOR_{ink.upper()}", curses.COLOR_WHITE)
        geo = tmux("display", "-p", "#{client_cell_width} #{client_cell_height}").split()
        self.ay = (int(geo[1]) / 4) / (int(geo[0]) / 2) if len(geo) == 2 and geo[0].isdigit() and int(geo[0]) else 1.25
        self.resize()

    # per layer: where its mist line sits, how high its peaks reach above
    # that (fractions of the height), how much ink, how far the ink runs down
    LAYERS = ((0.58, 0.46, 0.42, 0.075), (0.74, 0.32, 0.62, 0.065), (0.93, 0.22, 0.88, 0.06))

    def peaks(self, layer):
        """Peaks of a ridge layer as (world x, height, half-width): a few tall
        pointed ones, the way shan shui stacks mountains, not rolling hills."""
        r = random.Random(self.seed * 10 + layer)
        out, wx = [], -r.uniform(0, 60)
        while wx < self.WW + 60:
            out.append((wx, r.uniform(0.35, 1.0), r.uniform(14, 34)))
            wx += r.uniform(55, 150)
        return out

    def ridge(self, layer, wx):
        """Crest (dot row) of a ridge layer at world x."""
        base, reach = self.LAYERS[layer][:2]
        # rounded tops, steep flanks: shan shui peaks rise like fingers
        top = max((h * math.exp(-(abs(wx - px) / w) ** 2.2) for px, h, w in self.ridges[layer]), default=0)
        jag = 0.03 * math.sin(wx * 0.31 + layer) + 0.02 * math.sin(wx * 0.77)
        return self.H * (base - reach * (top + jag * top))

    def resize(self):
        s = self.s
        self.W, self.H = 2 * s.w, 4 * s.h
        self.ox, self.WW = s.x0 * 2, s.world_w * 2
        self.ridges = [self.peaks(layer) for layer in range(3)]
        self.dots, self.near = set(), set()
        # far to near: each ridge hides what's behind it, ink heaviest at the
        # crest and thinning down into mist (liubai: the mist is unpainted)
        for layer, (_, _, ink, fade) in enumerate(self.LAYERS):
            for x in range(self.W):
                wx = x + self.ox
                top = int(self.ridge(layer, wx))
                for y in range(max(0, top), self.H):
                    self.dots.discard((x, y))
                    self.near.discard((x, y))
                    # the ink runs further down some flanks than others
                    d = (y - top) / (self.H * fade * (0.7 + 0.6 * hash01(wx // 6, layer, 50)))
                    b = ink * math.exp(-d * d)
                    if b > 0.04 and b > DITHER[y % 64][wx % 64]:
                        self.dots.add((x, y))
                        if layer == 2:
                            self.near.add((x, y))
        self.born = {}

    def curls(self, now, dots):
        first = int((now - self.LIFE) // self.SLOT)
        for k in [k for k in self.born if k < first]:
            del self.born[k]
        for k in range(first, int(now // self.SLOT) + 1):
            t0 = k * self.SLOT
            if t0 > now:
                continue
            if k not in self.born:
                r = random.Random(k * 7919 + 13)
                band = r.choice((0, 1, 1, 2))   # drift in the mist band of a ridge layer
                self.born[k] = None if r.random() > 0.5 else (
                    r.uniform(-0.2, 1.0) * self.WW, band, r.uniform(10, 22), r.uniform(1.4, 2.4),
                    r.uniform(0, 6.28), r.choice((-1, 1)) * r.uniform(0.12, 0.3), r.uniform(14, 32),
                    r.uniform(0.7, 1.3), r.uniform(2.0, 3.6))
            if self.born[k] is None:
                continue
            x0, band, size, turns, rot0, spin, tail, speed, width = self.born[k]
            age = now - t0
            wx = x0 + 6.0 * speed * wind_travel(t0, now)
            y = self.H * (self.LAYERS[band][0] - 0.06) - size / self.ay
            reveal = min(1.0, age / 5.0)                       # painted on
            fray = clamp((age - self.LIFE * 0.55) / (self.LIFE * 0.4), 0.0, 1.0)  # dries out
            pts = curl_path(wx - self.ox, y, size, turns, rot0 + spin * age, tail, math.pi * 0.95, self.ay)
            brush(dots, pts, lambda t, w=width: w * (0.35 + 0.65 * math.sin(math.pi * min(1.0, 0.15 + t * 1.1))),
                  k, fray, reveal)

    def frame(self, now):
        s = self.s
        dots, near = set(self.dots), set(self.near)
        self.curls(now, dots)
        draw_cells(s, dots, near, self.W, self.H, self.ink)
        if self.side == "right" and s.w > 8 and s.h > 4:  # the seal: zen, in red
            for dy in range(2):
                s.put(s.h - 3 + dy, s.w - 6, "    ", curses.COLOR_RED, curses.A_REVERSE)
            s.put(s.h - 3, s.w - 5, "\u7985", curses.COLOR_RED, curses.A_REVERSE | curses.A_BOLD)


# ---------------------------------------------------------------- gallery

GALLERY = os.path.expanduser("~/.cache/zen/gallery")  # filled by zen-gallery.py


def read_png(path, max_side=2000, rgb=False):
    """A non-interlaced 8-bit PNG (gray, gray+alpha, RGB or RGBA) as
    (width, height, rows of 0..1 luminance), or of (r, g, b) 0..255 tuples
    with rgb=True. Stdlib only: PNG is zlib."""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")
    pos, idat, w = 8, [], 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or interlace or ctype not in (0, 2, 4, 6) or not (0 < w <= max_side and 0 < h <= max_side):
                raise ValueError("unsupported PNG")
            bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + n
    raw = zlib.decompress(b"".join(idat))
    stride, rows, prev = w * bpp, [], bytearray(w * bpp)
    for y in range(h):
        ftype, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):  # undo the row filter
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 255
            elif ftype == 2:
                line[i] = (line[i] + b) & 255
            elif ftype == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif ftype == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        if rgb:
            rows.append([(line[i], line[i], line[i]) if ctype in (0, 4) else tuple(line[i:i + 3])
                         for i in range(0, stride, bpp)])
        elif ctype in (0, 4):
            rows.append([line[i] / 255 for i in range(0, stride, bpp)])
        else:
            rows.append([(0.299 * line[i] + 0.587 * line[i + 1] + 0.114 * line[i + 2]) / 255
                         for i in range(0, stride, bpp)])
    return w, h, rows


def box_blur(rows, r):
    """Separable box blur of a 2-D list, radius r (clamped edges)."""
    def blur1(line):
        n, out, acc = len(line), [], 0.0
        pref = [0.0]
        for v in line:
            acc += v
            pref.append(acc)
        for i in range(n):
            lo, hi = max(0, i - r), min(n, i + r + 1)
            out.append((pref[hi] - pref[lo]) / (hi - lo))
        return out
    rows = [blur1(row) for row in rows]
    cols = [blur1(list(col)) for col in zip(*rows)]
    return [list(row) for row in zip(*cols)]


# ANSI hues by angle; blue is drawn bold (bright) so it reads on black
HUES = [(0, "RED"), (55, "YELLOW"), (120, "GREEN"), (185, "CYAN"), (235, "BLUE"), (300, "MAGENTA")]


def painting_ink(path):
    """The painting's dominant saturated hue as an ANSI colour name (white
    if it's mostly neutral), from a small colour thumbnail."""
    try:
        _, _, rows = read_png(path, rgb=True)
    except (OSError, ValueError, zlib.error):
        return None
    sx = sy = wsum = 0.0
    for row in rows:
        for r, g, b in row:
            mx, mn = max(r, g, b), min(r, g, b)
            if mx < 40 or mx - mn < 30:
                continue
            sat = (mx - mn) / mx
            if mx == r:
                h = (60 * (g - b) / (mx - mn)) % 360
            elif mx == g:
                h = 60 * (b - r) / (mx - mn) + 120
            else:
                h = 60 * (r - g) / (mx - mn) + 240
            sx += sat * math.cos(math.radians(h))
            sy += sat * math.sin(math.radians(h))
            wsum += sat
    n = sum(len(row) for row in rows) or 1
    if wsum / n < 0.06:
        return "WHITE"
    hue = math.degrees(math.atan2(sy, sx)) % 360
    return min(HUES, key=lambda hn: min(abs(hue - hn[0]), 360 - abs(hue - hn[0])))[1]


def srgb_lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin_srgb(c):
    c = clamp(c, 0.0, 1.0)
    return round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))


def oklab(r, g, b):
    """Linear sRGB (0..1) to Oklab: L lightness, a/b colour, perceptually even."""
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def xterm256():
    """The xterm 256-colour palette beyond the 16 user-set colours: the 6x6x6
    cube and the gray ramp, as (index, linear rgb)."""
    out, lv = [], [0, 95, 135, 175, 215, 255]
    for i in range(216):
        out.append((16 + i, (lv[i // 36], lv[i // 6 % 6], lv[i % 6])))
    for i in range(24):
        out.append((232 + i, (8 + 10 * i,) * 3))
    return [(n, tuple(srgb_lin(c) for c in rgb)) for n, rgb in out]


def dots4(states):
    """Eight 0..3 dot states (braille order) as a Zen Dots character."""
    n = sum(v * 4 ** i for i, v in enumerate(states))
    return " " if n == 0 else "\u2588" if n == 4 ** 8 - 1 else chr(0x100000 + n)


BAYER2 = [[0, 2], [3, 1]]
DOT_ORDER = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)]  # braille order


def plaque_words(png, pick=0):
    """One take on a painting: wall text and the critic's version
    (zen-gallery.py --plaques). A painting has several; pick chooses."""
    try:
        with open(png[:-4] + ".plaque.json") as f:
            words = json.load(f)
    except (OSError, ValueError):
        return {}
    takes = words.get("takes") or [words]  # (the one-take format)
    take = takes[pick % len(takes)] if takes else {}
    out = {k: re.sub(r"[^\w .,;:'!?()&\-\u2013\u2014/\"]", "", str(take.get(k) or take.get("critic", "")))[:400]
           for k in ("plaque", "spoken")}
    out["angle"] = take.get("angle", 2) if isinstance(take.get("angle", 2), int) else 2
    return out


class Gallery:
    """A famous public-domain painting, dithered, across the whole window
    (your work hangs in front of its middle), with a museum caption. The
    painting is picked per toggle from ~/.cache/zen/gallery (zen-gallery.py
    fills it), or by @zen-painting (an AIC id or part of a title).
    @zen-gallery-frame: auto (default: a landscape is split, each spacer showing
    its own half so nothing hides behind your work; a portrait or square one
    hangs whole, at its true shape, with a second one opposite as its
    pendant), split, whole, or span (one painting across the window, its
    middle behind your work).
    Colour: the painting's own, per cell, blended toward the background
    (@zen-gallery-blend; 0.3 on dark, 0.05 on light). @zen-gallery-palette
    picks the inks: 256 (default on dark: the xterm 256-colour cube and gray
    ramp, your 16-colour palette left alone), both (default on light: the
    cube plus your terminal's own 16), ansi (only your 16), rgb (24-bit, each
    cell its exact colour), or mono: one ink for the whole painting, @zen-ink
    (a colour, or random), else the painting's own dominant colour; mono also
    lets @zen-pixels dots use the Zen Dots font (4 levels). (Style
    gallery-color is an old alias of gallery.) The
    background is asked of the terminal at startup (@zen-bg overrides); on a
    light one the dots become ink on paper, drawn where the painting is dark.
    @zen-gallery-ground on|off: a background shade per cell under the
    dots (default on for a light background).
    Rotation: every @zen-gallery-rotate minutes (default 5, 0 = never) the
    next painting, on the shared clock so both sides turn together: the old
    one dissolves dot by dot into the background, the spacer respawns (and so
    re-asks the terminal for its colours), the new one condenses back."""
    fps = 1
    FADE = 4.0     # seconds to dissolve out, and again to condense in

    def __init__(self, s, side):
        self.s, self.side = s, side
        self.frame_opt = opt("zen-gallery-frame") or "auto"
        self.color = opt("zen-gallery-palette") != "mono"  # mono: the single-ink gallery
        hexbg = (opt("zen-bg") or "").lstrip("#")
        self.bg = (tuple(srgb_lin(int(hexbg[i:i + 2], 16)) for i in (0, 2, 4))
                   if re.fullmatch(r"[0-9a-fA-F]{6}", hexbg) else TERM_BG or (0.0, 0.0, 0.0))
        # on a light background dots are ink on paper: drawn where it's dark
        self.light = 0.2126 * self.bg[0] + 0.7152 * self.bg[1] + 0.0722 * self.bg[2] > 0.25
        self.dots = opt("zen-pixels") == "dots"
        # the ground (see paint_ground): on by default on paper, where dots alone are too faint
        self.ground = opt("zen-gallery-ground") == "on" or (self.light and opt("zen-gallery-ground") != "off")
        # braille dots cover maybe a third of a cell: light dots on dark glow
        # past that, dark dots on paper can't get dark enough. So on a light
        # background octants (solid sub-cells) unless @zen-pixels says otherwise
        self.octant = PIXELS in ("octant", "mixed") or (self.light and not opt("zen-pixels"))
        try:
            self.period = max(0.0, float(opt("zen-gallery-rotate") or 5)) * 60
        except ValueError:
            self.period = 300.0
        if opt("zen-painting"):
            self.period = 0.0  # a chosen painting stays
        self.slot = int(time.time() // self.period) if self.period else 0
        self.respawn = False
        self.born = time.time()
        self.seq = []
        self.art = self.pick()
        ink = (opt("zen-ink") or (self.art and self.art[4]) or "white").upper()
        if ink == "RANDOM":
            ink = random.Random(int(os.environ.get("ZEN_SEED", "0")) + 1).choice([h for _, h in HUES] + ["WHITE"])
        self.ink = getattr(curses, f"COLOR_{ink}", curses.COLOR_WHITE)
        self.attr = curses.A_BOLD if ink == "BLUE" else 0
        if not opt("zen-ink"):  # a painting's own colour may not read on this background
            idx = self.readable_ink(self.ink + (8 if self.attr else 0))
            self.ink, self.attr = idx % 8, curses.A_BOLD if idx >= 8 else 0
        self.resize()

    def pick(self):
        metas = []
        for path in sorted(glob.glob(os.path.join(GALLERY, "*.json"))):
            if path.endswith(".plaque.json"):
                continue
            try:
                with open(path) as f:
                    m = json.load(f)
                metas.append((m, path[:-5] + ".png"))
            except (OSError, ValueError):
                pass
        want = (opt("zen-painting") or "").lower()
        chosen = [x for x in metas if want and (want == str(x[0].get("id")) or want in str(x[0].get("title", "")).lower())]
        pool = chosen or metas
        if not pool:
            return None
        seed = int(os.environ.get("ZEN_SEED", "0"))
        # rotating: the slot of the shared clock picks, so both sides agree
        idx = (seed + self.slot) % len(pool) if self.period else random.Random(seed).randrange(len(pool))

        def tall(item):  # portrait or squarish: hangs whole rather than split
            try:
                with open(item[1], "rb") as f:
                    pw, ph = struct.unpack(">II", f.read(24)[16:24])
                return pw / ph < 1.25
            except (OSError, struct.error, ZeroDivisionError):
                return False
        self.mode = {"auto": "whole" if tall(pool[idx]) else "split"}.get(self.frame_opt, self.frame_opt)
        if self.mode not in ("split", "whole", "span"):
            self.mode = "split"
        pend = idx
        if self.mode == "whole":  # the pendant opposite: the next tall one
            for j in range(1, len(pool)):
                if tall(pool[(idx + j) % len(pool)]):
                    pend = (idx + j) % len(pool)
                    break
        left_png = pool[idx][1]
        if self.mode == "whole" and self.side == "right":
            idx = pend
        meta, png = pool[idx]
        try:
            w, h, rows = read_png(png)
        except (OSError, ValueError, zlib.error):
            return None
        self.rgb = None
        if self.color:  # the colour copy, as linear rgb
            try:
                cw, ch, crow = read_png(png[:-4] + "-color.png", rgb=True)
                self.rgb = (cw, ch, [[tuple(srgb_lin(c) for c in px) for px in row] for row in crow])
            except (OSError, ValueError, zlib.error):
                pass
        # sharpen (unsharp mask) so edges survive the dither, then stretch the
        # levels (2nd..98th percentile) so dark paintings still read
        soft = box_blur(rows, max(1, w // 200))
        rows = [[v + 0.9 * (v - b) for v, b in zip(row, brow)] for row, brow in zip(rows, soft)]
        flat = sorted(v for row in rows[::4] for v in row[::4])
        lo, hi = flat[len(flat) // 50], flat[-len(flat) // 50 - 1]
        span = max(0.05, hi - lo)
        rows = [[min(1.0, max(0.0, (v - lo) / span)) ** 1.25 for v in row] for row in rows]  # a bit of midtone contrast
        caption = [str(meta.get("artist", ""))[:60], str(meta.get("title", ""))[:60], str(meta.get("date", ""))[:40]]
        # a different take each time it comes around (or each toggle)
        take = self.slot // max(1, len(pool)) if self.period else seed
        # what gets said, in order, and in which panel: with pendants the left
        # painting's take in the left panel, then the right one's in the
        # right (both sides load both, so they agree on the timing); one
        # painting across both panels gets one take, in the right panel
        if self.mode == "whole":
            first = plaque_words(left_png, take)
            who = self.ANGLE_CAST[first.get("angle", 2) % len(self.ANGLE_CAST)]
            second = {}
            for j in range(1, 8):  # the opposite painting's take: someone else speaks it
                second = plaque_words(pool[pend][1], take + j)
                if self.ANGLE_CAST[second.get("angle", 2) % len(self.ANGLE_CAST)] != who:
                    break
            self.seq = [("left", first), ("right", second)]
        else:
            self.seq = [("right", plaque_words(png, take))]
        self.seq = [(side, w) for side, w in self.seq if w.get("plaque")]
        return (w, h, rows, [re.sub(r"[^\w .,;:'&()\-\u2013\u2014/]", "", c) for c in caption],
                painting_ink(png[:-4] + "-color.png"))

    def resize(self):
        s = self.s
        self.W, self.H = 2 * s.w, 4 * s.h
        self.ox, self.WW = s.x0 * 2, s.world_w * 2
        self.cells = {}
        self.dotr = []  # (cell, dot bit, r): a dot shows while the fade level k >= r
        if not self.art:
            return
        w, h, rows = self.art[:3]
        # a braille dot is cell_h/4 tall by cell_w/2 wide: 1.25 wide-units
        # tall in a 14x35 cell, so measure y in dot widths to keep the shape
        geo = tmux("display", "-p", "#{client_cell_width} #{client_cell_height}").split()
        ay = (int(geo[1]) / 4) / (int(geo[0]) / 2) if len(geo) == 2 and geo[0].isdigit() and int(geo[0]) else 1.0
        if self.mode == "split":    # this spacer's half of the painting, covering the panel
            x0 = 0 if self.side == "left" else w / 2
            pw, frame_w, fx = w / 2, self.W, 0
        elif self.mode == "whole":  # all of it, at its own shape, with a margin
            x0, pw, frame_w, fx = 0, w, self.W, 0
        else:                       # one painting across the window
            x0, pw, frame_w, fx = 0, w, self.WW, self.ox
        if self.mode == "whole":    # contain: fit inside, leaving wall around it
            scale = min(frame_w * 0.88 / pw, self.H * ay * 0.8 / h)
            cy = (h - self.H * ay / scale) / 2 - 2 * ay / scale  # a little above centre, room for the plate
        else:                       # cover: fill, cropping the overflow evenly
            scale = max(frame_w / pw, self.H * ay / h)
            cy = (h - self.H * ay / scale) / 2
        cx = x0 + (pw - frame_w / scale) / 2

        def tone(x, y):  # how much ink this dot wants: light on dark, dark on light
            sy, sx = cy + (y + 0.5) * ay / scale, cx + (x + fx + 0.5) / scale
            if not (0 <= sy < h and 0 <= sx < w):
                return 0.0  # the wall around a hung painting
            v = rows[int(sy)][int(sx)]
            return 1 - v if self.light else v
        if self.ground:
            self.paint_ground(tone, scale, cx, cy, ay, fx, w, h)
            return
        if self.rgb:
            self.paint_color(tone, scale, cx, cy, ay, fx, w, h)
            return
        if self.dots:  # 4 levels per dot, ordered dither between neighbouring levels
            for row in range(self.H // 4):
                for col in range(self.W // 2):
                    states = []
                    for c, r in DOT_ORDER:
                        lvl = tone(col * 2 + c, row * 4 + r) * 3
                        lo = int(lvl)
                        states.append(min(3, lo + (lvl - lo > (BAYER2[r % 2][c] + 0.5) / 4)))
                    if any(states):
                        self.cells[(row, col)] = dots4(states)
            return
        for y in range(self.H):
            for x in range(self.W):
                wx = x + self.ox
                v = tone(x, y)
                if v > 0.04 and v > DITHER[y % 64][wx % 64]:
                    key = (y // 4, x // 2)
                    self.cells[key] = self.cells.get(key, 0) | Braille.BIT[(x % 2, y % 4)]
                    self.dotr.append((key, Braille.BIT[(x % 2, y % 4)], DITHER[y % 64][wx % 64] / v))

    LIFT = 1.3     # tone -> dot density: a little contrast so shapes hold together

    def paint_color(self, tone, scale, cx, cy, ay, fx, w, h):
        """Braille in 256 colours, with lightness and colour split the way the
        eye splits them (JPEG's chroma subsampling, more or less):

        - the dots carry lightness: density is the ordered dither of the
          painting's tone, exactly as in black and white, so it stays legible;
        - each cell's one ink colour carries hue: the painting's colour under
          the cell at full brightness, blended toward the background
          (@zen-gallery-blend, 0..1, default 0.3), on a light background the inks deepened,
          matched to the xterm 256-colour cube in Oklab, and the colour it
          misses by is passed on to the next cells (Floyd-Steinberg), so
          neighbouring dots mix toward the true hue the way Seurat's do."""
        cw, ch, lin = self.rgb
        # inks: the 256-colour cube, and/or the terminal's own 16 (e.g. an
        # ansil16 palette, made to read on its background); @zen-gallery-palette
        # 256 | ansi | both | rgb (24-bit: every cell its exact colour, no
        # palette at all), default both on a light background, 256 on dark
        which = opt("zen-gallery-palette") or ("both" if self.light else "256")
        pal = [(n, rgb, oklab(*rgb)) for n, rgb in xterm256()] if which != "ansi" else []
        if which in ("ansi", "both") and TERM_PALETTE:
            bgl = oklab(*self.bg)
            pal += [(n, rgb, oklab(*rgb)) for n, rgb in sorted(TERM_PALETTE.items())
                    if sum((a - b) ** 2 for a, b in zip(oklab(*rgb), bgl)) > 0.01]  # not the background itself
        pal = pal or [(n, rgb, oklab(*rgb)) for n, rgb in xterm256()]
        default = 0.0  # full colour; @zen-gallery-blend raises it (toward the background)
        try:
            blend = clamp(float(opt("zen-gallery-blend") or default), 0.0, 0.95)
        except ValueError:
            blend = default
        bg = self.bg
        depth = 0.3 if self.light else 1.0  # on paper the inks are deep versions of the colours
        rows_, cols_ = self.H // 4, self.W // 2
        err = [[(0.0, 0.0, 0.0)] * (cols_ + 2) for _ in range(rows_ + 2)]
        memo = {}

        def color_at(x, y):  # linear rgb of the painting under dot (x, y)
            px = (cx + (x + fx + 0.5) / scale) / w * cw
            py = (cy + (y + 0.5) * ay / scale) / h * ch
            return lin[min(ch - 1, max(0, int(py)))][min(cw - 1, max(0, int(px)))]

        self.ccells = {}
        for row in range(rows_):
            for col in range(cols_):
                dots = [(col * 2 + c, row * 4 + r) for c, r in DOT_ORDER]
                bits = 0
                for x, y in dots:  # lightness: dot density, as in black and white
                    t = tone(x, y)
                    d = DITHER[y % 64][(x + self.ox) % 64]
                    if t > 0.04 and t ** self.LIFT > d:
                        bits |= Braille.BIT[(x % 2, y % 4)]
                        self.dotr.append(((row, col), Braille.BIT[(x % 2, y % 4)], d / t ** self.LIFT))
                avg = [sum(color_at(x, y)[i] for x, y in dots) / 8 for i in range(3)]
                peak = max(avg)
                full = [depth * v / peak for v in avg] if peak > 1e-4 else [depth] * 3  # its hue, full (or deep on paper)
                e = err[row][col]
                target = tuple(clamp((1 - blend) * full[i] + blend * bg[i] + e[i], 0.0, 1.0) for i in range(3))
                if not bits:  # nothing drawn here: carry the colour on untouched
                    err[row][col + 1] = tuple(err[row][col + 1][i] + (target[i] - (1 - blend) * full[i] - blend * bg[i]) for i in range(3))
                    continue
                if which == "rgb":  # truecolor: no matching, nothing left over to carry
                    self.ccells[(row, col)] = (self.glyph(bits), "0;38;2;%d;%d;%d" % tuple(lin_srgb(v) for v in target))
                    continue
                key = tuple(round(v * 48) for v in target)
                if key not in memo:
                    tl = oklab(*target)
                    memo[key] = min(pal, key=lambda q: 0.5 * (q[2][0] - tl[0]) ** 2 + (q[2][1] - tl[1]) ** 2 + (q[2][2] - tl[2]) ** 2)
                n, rgb, _ = memo[key]
                left = [target[i] - rgb[i] for i in range(3)]
                for dr, dc, wgt in ((0, 1, 7 / 16), (1, -1, 3 / 16), (1, 0, 5 / 16), (1, 1, 1 / 16)):
                    o = err[row + dr][col + dc]
                    err[row + dr][col + dc] = tuple(o[i] + left[i] * wgt for i in range(3))
                self.ccells[(row, col)] = (self.glyph(bits), f"0;38;5;{n}")

    def palette16(self):
        return TERM_PALETTE or {i: tuple(srgb_lin(c) for c in rgb) for i, rgb in enumerate(
            [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229)])}

    def readable_ink(self, idx):
        """Palette index idx, or if it's too close to the background to read
        (say a yellow on paper), the readable palette colour nearest in hue."""
        pal = self.palette16()
        bl = oklab(*self.bg)
        il = oklab(*pal.get(idx, (0.8, 0.8, 0.8)))
        if abs(il[0] - bl[0]) >= 0.35:
            return idx
        ok = [i for i, c in pal.items() if abs(oklab(*c)[0] - bl[0]) >= 0.35]
        hue = math.atan2(il[2], il[1])

        def hue_gap(i):
            lab = oklab(*pal[i])
            return abs((math.atan2(lab[2], lab[1]) - hue + math.pi) % (2 * math.pi) - math.pi)
        return min(ok, key=hue_gap) if ok else min(pal, key=lambda i: oklab(*pal[i])[0] if self.light else -oklab(*pal[i])[0])

    def ink_lin(self):
        return self.palette16().get(self.ink + (8 if self.attr & curses.A_BOLD else 0), (0.8, 0.8, 0.8))

    GCOVER = 0.35   # how much of a cell a full set of braille dots covers

    def paint_ground(self, tone, scale, cx, cy, ay, fx, w, h):
        """Braille with a ground (@zen-gallery-ground on): each cell's
        background colour carries the coarse tone (the cell's ink, blurred
        over its neighbours), and its dots the detail around it: ink dots
        where a spot is darker than the ground, paper dots where it's lighter.
        Dots alone only reach a third of the way to ink; with the ground, the
        full range. 24-bit colour, so the ground can be any shade."""
        rows_, cols_ = self.H // 4, self.W // 2
        lin = self.rgb[2] if self.rgb else None
        mono = self.ink_lin()

        def ink_at(dots):  # this cell's ink: the painting's colour, deep on paper
            if not lin:
                return mono
            cw, ch = self.rgb[0], self.rgb[1]
            avg = [0.0, 0.0, 0.0]
            for x, y in dots:
                px = (cx + (x + fx + 0.5) / scale) / w * cw
                py = (cy + (y + 0.5) * ay / scale) / h * ch
                c = lin[min(ch - 1, max(0, int(py)))][min(cw - 1, max(0, int(px)))]
                avg = [a + v / 8 for a, v in zip(avg, c)]
            peak = max(avg)
            depth = 0.25 if self.light else 1.0
            return tuple(depth * v / peak for v in avg) if peak > 1e-4 else mono

        cells, means = [], {}
        for row in range(rows_):
            for col in range(cols_):
                dots = [(col * 2 + c, row * 4 + r) for c, r in DOT_ORDER]
                tones = [tone(x, y) for x, y in dots]
                means[(row, col)] = sum(tones) / 8
                cells.append(((row, col), tones, [DITHER[y % 64][(x + self.ox) % 64] for x, y in dots],
                              dots, ink_at(dots)))
        # the ground follows a blurred tone, so neighbouring cells' shades step
        # gently and the dots carry the edges
        self.gcells = []
        for key, tones, ds, dots, ink in cells:
            r, c = key
            near = [means[(r + i, c + j)] for i in (-1, 0, 1) for j in (-1, 0, 1) if (r + i, c + j) in means]
            self.gcells.append((key, tones, ds, dots, ink, sum(near) / len(near)))
        self.ccells = self.render_ground(1.0)

    def render_ground(self, k):
        out, paper = {}, self.bg
        for key, tones, ds, dots, ink, m in self.gcells:
            a, ts = m * k, [t * k for t in tones]
            if a < 0.02 and max(ts) < 0.06:
                continue  # bare paper
            bits = 0
            if a < 0.5:   # light area: a lighter ground, ink dots for the darker spots
                b = max(0.0, a - self.GCOVER * 0.5)
                fg = ink
                for (x, y), t, d in zip(dots, ts, ds):
                    if (t - b) / (self.GCOVER * (1 - b)) > d:
                        bits |= Braille.BIT[(x % 2, y % 4)]
            else:         # dark area: a deep ground, paper dots for the lighter spots
                b = min(1.0, a + self.GCOVER * 0.5)
                fg = paper
                for (x, y), t, d in zip(dots, ts, ds):
                    if (b - t) / (self.GCOVER * b) > d:
                        bits |= Braille.BIT[(x % 2, y % 4)]
            bg = tuple(p + (i - p) * b for p, i in zip(paper, ink))
            sgr = "0;38;2;%d;%d;%d;48;2;%d;%d;%d" % (tuple(lin_srgb(v) for v in fg) + tuple(lin_srgb(v) for v in bg))
            out[key] = (chr(0x2800 + bits) if bits else " ", sgr)
        return out

    def glyph(self, bits):
        return OCTANTS[bits] if self.octant else chr(0x2800 + bits)

    # the cast: 16x16 pixels each (octants: 8 columns x 4 rows). e = eye,
    # o = only while talking, c = only while quiet. Each speaks some angles
    # (zen-gallery.py ANGLES): composition the artist, technique the
    # painter, subject and art history the critic, the period the
    # professor, the gut reaction the everyman
    CAST = {
        "critic": [            # bowler, moustache; the mouth opens under it
            "....XXXXXXXX....",
            "...XXXXXXXXXX...",
            "...XXXXXXXXXX...",
            "...XXXXXXXXXX...",
            ".XXXXXXXXXXXXXX.",
            "...X........X...",
            "...X..e..e..X...",
            "...X........X...",
            "...X.XXXXXX.X...",
            "...X...oo...X...",
            "....X......X....",
            ".....XXXXXX.....",
            "......X..X......",
            "....XX.XX.XX....",
            "...XXXXXXXXXX...",
            "..XXXXXXXXXXXX..",
        ],
        "artist": [            # slouched beret, a big goatee; a mouth appears above it as he talks
            "......XX........",
            "...XXXXXXXX.....",
            ".XXXXXXXXXXXX...",
            ".XXXXXXXXXXXXX..",
            "...XXXXXXXXXX...",
            "...X........X...",
            "...X..e..e..X...",
            "...X........X...",
            "...X........X...",
            "...X...oo...X...",
            "....X.XXXX.X....",
            ".....XXXXXX.....",
            "......XXXX......",
            ".......XX.......",
            "...XXXXXXXXXX...",
            "..XXXXXXXXXXXX..",
        ],
        "painter": [           # straight bangs, a high ponytail that swings as she talks
            ".........XXX....",
            ".....XXXXXX.XXX.",
            "....XXXXXXXX.XXX",
            "...XXXXXXXXXX.XX",
            "...XXXXXXXXXX.XX",
            "...X........X.XX",
            "...X..e..e..X.tT",
            "...X........X.tT",
            "...X........X...",
            "...X...oo...X...",
            "....X......X....",
            ".....XXXXXX.....",
            ".......XX.......",
            "....XXXXXXXX....",
            "...XXXXXXXXXX...",
            "..XXXXXXXXXXXX..",
        ],
        "professor": [         # hair up in a bun, opaque glasses with a glint, pearls
            "................",
            ".......XXX......",
            ".......XXX......",
            ".....XXXXXXX....",
            "....XXXXXXXXX...",
            "...XX.......XX..",
            "...X.gXh.gXh.X..",    # g/h top corners, G centre: a glint is a
            "...X.XGXXXGX.X..",    # corner plus the centre, a diagonal streak
            "...X.XXX.XXX.X..",
            "...X...ooo...X..",
            "....X.......X...",
            ".....XXXXXXX....",
            ".......X.X......",
            ".....X.X.X.X....",
            "...XXXXXXXXXXX..",
            "..XXXXXXXXXXXXX.",
        ],
    }
    CAST["everyman"] = [       # the hussar (drawn by Tony): busby with a tassel
        "...XXXXXXXXXX...",    # (t at rest, T swung), drooping moustache,
        "...XXXXXXXXXXX..",    # mutton chops into the jaw, collar, braided coat
        "...XXXXXXXXXX.X.",
        "...XXXXXXXXXX.tT",
        "...XXXXXXXXXX...",
        "...X........X...",
        "...X..e..e..X...",
        "...X........X...",
        "..XX.XXXXXX.XX..",
        "..XX.X.oo.X.XX..",
        "..XXX......XXX..",
        "...XXXX..XXXX...",
        "......X..X......",
        ".XXXXX....XXXXX.",
        "..XX.XXXXXX.XX..",
        "..XXX..XX..XXX..",
    ]
    ANGLE_CAST = ["artist", "painter", "critic", "critic", "professor", "everyman"]
    TYPE_RATE = 24.0   # characters a second

    def cast_mask(self, who):
        """The cells a figure covers: per pixel row, everything between its
        leftmost and rightmost mark (so faces are filled in), at cell size."""
        cells = set()
        for y, line in enumerate(self.CAST.get(who, self.CAST["critic"])):
            marks = [x for x, c in enumerate(line) if c != "."]
            for x in range(min(marks), max(marks) + 1) if marks else ():
                cells.add((y // 4, x // 2))
        return cells

    def cast_cells(self, who, mouth, look, blink, swing=False, glint=None):
        # glint: which top corner of her lenses catches the light (-1 left,
        # +1 right, 0 none); by default the inner one, away from the side
        # she looks to, so it never lands flush against her face outline
        glint = -look if glint is None else glint
        bits = {}
        for y, line in enumerate(self.CAST.get(who, self.CAST["critic"])):
            for x, c in enumerate(line):
                on = (c == "X" or (c == "o" and mouth) or (c == "c" and not mouth)
                      or (c == "t" and not swing) or (c == "T" and swing)
                      or (c == "g" and glint != -1) or (c == "h" and glint != 1)
                      or (c == "G" and not glint))
                if c == "e" and not blink:
                    x, on = x + look, True       # eyes shift as he looks around
                elif who == "professor" and 6 <= y <= 8 and 5 <= x <= 11:
                    x += look                    # her glasses nudge as she looks around
                if on:
                    key = (y // 4, x // 2)
                    bits[key] = bits.get(key, 0) | Braille.BIT[(x % 2, y % 4)]
        return bits

    def docent(self, now):
        """Draw the cast or the plaque (@zen-gallery-docent: cast, plaque or
        none) at the bottom of the panels, each take next to its painting:
        whoever owns the take's angle stands at the panel's inner corner and
        types it out, mouth going, finished lines scrolling up. With pendants
        the left painting gets its say first, then the speaker pops across to
        the right one. Returns True while typing in this panel."""
        kind = opt("zen-gallery-docent") or "cast"
        if kind == "critic":
            kind = "cast"
        if kind not in ("plaque", "cast") or not self.seq:
            return False
        s = self.s
        t = now - ((self.slot * self.period + self.FADE + 1) if self.period else self.born + 2)
        texts = [w["plaque"] if kind == "plaque" else w["spoken"] for _, w in self.seq]
        pause = 5.0
        starts, at = [], 0.0
        for txt in texts:
            starts.append(at)
            at += len(txt) / self.TYPE_RATE + pause
        active = max((i for i, st in enumerate(starts) if t >= st), default=-1)
        mine = [i for i, (side, _) in enumerate(self.seq) if side == self.side]
        if not mine or t < starts[mine[0]]:
            return False   # not this panel's turn yet
        k = mine[0]
        text = texts[k]
        shown = int((t - starts[k]) * self.TYPE_RATE)
        sprite = 9 if kind == "cast" else 0
        width = max(10, s.w - sprite - 4)
        lines = textwrap.wrap(text, width)
        base = s.h - 4                          # the speaker's top row (4 rows tall)
        say = base + 2 if kind == "cast" else s.h - 2   # the line being typed: level with the mouth
        upto, cur = shown, len(lines) - 1
        for i, line in enumerate(lines):        # which line is being typed, and how far
            if upto <= len(line):
                cur = i
                break
            upto -= len(line) + 1
        else:
            upto = len(lines[-1])
        # the speaker stands at the panel's inner corner (by your work), the
        # words to the outer side of them
        sx = s.w - sprite - 1 if self.side == "left" else 1
        tx = 1 if self.side == "left" else sprite + 2
        for i in range(max(0, cur - max(8, s.h // 3)), cur + 1):
            row = say - (cur - i)
            s.put(row, tx - 1, " " * (width + 2), self.ink)
            s.put(row, tx, lines[i] if i < cur else lines[i][:max(0, upto)], self.ink,
                  getattr(curses, "A_ITALIC", 0) if kind == "plaque" else 0)
        typing = active == k and shown < len(text)
        if kind == "cast" and active >= k:      # here from their turn on: done, they stay and look around
            who = self.ANGLE_CAST[self.seq[k][1].get("angle", 2) % len(self.ANGLE_CAST)]
            # no patch of wall: only the figure's own cells are cleared, so the
            # face is blank and the painting runs right up to the outline
            for row, col in self.cast_mask(who):
                s.put(base + row, sx + col, " ", self.ink)
            mouth = typing and int(now * 8) % 2 == 0
            # while talking they face their painting; then they look around
            look = (1 if self.side == "right" else -1) if typing else (-1, 0, 1, 0)[int(hash01(int(now // 2.5), 61) * 4)]
            blink = (now % 4.7) < 0.15
            # the professor's glasses glint on the inner corner as she glances
            # aside, and flash briefly now and then while she looks ahead
            glint = -look if look else (1 if (now % 3.7) < 0.6 else 0)
            # a tassel swings with the head as they talk, and now and then after
            swing = (int(now * 5) % 3 == 0) if typing else (now % 6.3) < 0.4
            for (row, col), bits in self.cast_cells(who, mouth, look, blink, swing, glint).items():
                s.put(base + row, sx + col, OCTANTS[bits], self.ink)
        return typing

    def fade(self, now):
        """1 = fully shown; toward 0 at the ends of a rotation slot."""
        if not self.period:
            return 1.0
        t = now % self.period
        return clamp(min(t, self.period - t) / self.FADE, 0.0, 1.0)

    def frame(self, now):
        s = self.s
        if self.period:
            if int(now // self.period) != self.slot:
                self.respawn = True  # the next painting (and a fresh look at the terminal's colours)
            left = self.period - now % self.period
            self.fps = 10 if left < self.FADE + 1 or now % self.period < self.FADE else 1
        if not self.art:
            s.put(s.h // 2, 1, "no paintings yet: run zen-gallery.py", self.ink)
            return
        k = self.fade(now)
        if self.ground:
            for (row, col), (ch, sgr) in (self.ccells if k >= 1 else self.render_ground(k)).items():
                s.put_sgr(row, col, ch, sgr)
        elif k < 1 and not self.dots:  # dissolving: only the dots whose threshold k still clears
            cells = {}
            for key, bit, r in self.dotr:
                if r <= k:
                    cells[key] = cells.get(key, 0) | bit
            for (row, col), bits in cells.items():
                if self.rgb:
                    s.put_sgr(row, col, self.glyph(bits), self.ccells[(row, col)][1])
                else:
                    s.put(row, col, self.glyph(bits), self.ink, self.attr)
        else:
            if self.rgb or self.ground:
                for (row, col), (ch, sgr) in self.ccells.items():
                    s.put_sgr(row, col, ch, sgr)
            for (row, col), cell in self.cells.items():
                s.put(row, col, cell if self.dots else self.glyph(cell), self.ink, self.attr)
        speaking = self.docent(now) if k >= 1 else False
        if self.period and k >= 1:
            self.fps = 12 if speaking else 4   # the typewriter; then blinks and glances
        elif not self.period:
            self.fps = 12 if speaking else 4 if self.seq else 1
        docent_here = any(side == self.side for side, _ in self.seq) and (opt("zen-gallery-docent") or "cast") != "none"
        if self.side == "right" or self.mode == "whole":  # the caption plate, an outer corner
            lines = [l for l in self.art[3] if l]
            width = min(s.w - 2, max(len(l) for l in lines) + 2)
            top = 0 if docent_here else s.h - len(lines) - 2   # the top, if the docent has the bottom
            left = s.w - width - 1 if self.side == "right" else 1
            for i in range(len(lines) + 2):
                s.put(top + i, left, " " * width, self.ink)
            for i, line in enumerate(lines):
                s.put(top + 1 + i, left + 1, line[:width - 2], self.ink,
                      curses.A_BOLD if i == 0 else getattr(curses, "A_ITALIC", 0) if i == 1 else curses.A_DIM)


# ---------------------------------------------------------------- matrix

# halfwidth katakana (single-cell) + digits
GLYPHS = [chr(c) for c in range(0xFF66, 0xFF9E)] + list("0123456789Z:.=*+<>")


# 5x5 block font for the host style; unknown chars render blank
FONT = {k: v.split("|") for k, v in {
    "A": " ### |#   #|#####|#   #|#   #", "B": "#### |#   #|#### |#   #|#### ",
    "C": " ####|#    |#    |#    | ####", "D": "#### |#   #|#   #|#   #|#### ",
    "E": "#####|#    |#### |#    |#####", "F": "#####|#    |#### |#    |#    ",
    "G": " ####|#    |#  ##|#   #| ####", "H": "#   #|#   #|#####|#   #|#   #",
    "I": "#####|  #  |  #  |  #  |#####", "J": "#####|   # |   # |#  # | ##  ",
    "K": "#   #|#  # |###  |#  # |#   #", "L": "#    |#    |#    |#    |#####",
    "M": "#   #|## ##|# # #|#   #|#   #", "N": "#   #|##  #|# # #|#  ##|#   #",
    "O": " ### |#   #|#   #|#   #| ### ", "P": "#### |#   #|#### |#    |#    ",
    "Q": " ### |#   #|# # #|#  # | ## #", "R": "#### |#   #|#### |#  # |#   #",
    "S": " ####|#    | ### |    #|#### ", "T": "#####|  #  |  #  |  #  |  #  ",
    "U": "#   #|#   #|#   #|#   #| ### ", "V": "#   #|#   #|#   #| # # |  #  ",
    "W": "#   #|#   #|# # #|## ##|#   #", "X": "#   #| # # |  #  | # # |#   #",
    "Y": "#   #| # # |  #  |  #  |  #  ", "Z": "#####|   # |  #  | #   |#####",
    "0": " ### |#  ##|# # #|##  #| ### ", "1": "  #  | ##  |  #  |  #  | ### ",
    "2": " ### |#   #|  ## | #   |#####", "3": "#### |    #| ### |    #|#### ",
    "4": "#   #|#   #|#####|    #|    #", "5": "#####|#    |#### |    #|#### ",
    "6": " ### |#    |#### |#   #| ### ", "7": "#####|    #|   # |  #  |  #  ",
    "8": " ### |#   #| ### |#   #| ### ", "9": " ### |#   #| ####|    #| ### ",
    "-": "     |     |#####|     |     ",
}.items()}


def block_text(text, width):
    """Lay text out in the block font, wrapping to fit width.
    Returns (pixels {(y, x): letter_index}, height, width), origin top-left."""
    per_line = max(1, (width + 1) // 6)
    lines = [text[i:i + per_line] for i in range(0, len(text), per_line)]
    pixels = {}
    bw = 0
    for li, line in enumerate(lines):
        bw = max(bw, len(line) * 6 - 1)
        for ci, ch in enumerate(line):
            for ry, row in enumerate(FONT.get(ch, [" " * 5] * 5)):
                for rx, p in enumerate(row):
                    if p != " ":
                        pixels[(li * 7 + ry, ci * 6 + rx)] = li * per_line + ci
    return pixels, len(lines) * 7 - 2, bw


class Drop:
    def __init__(self, h, rng, start=None):
        self.y = float(start if start is not None else -rng.randint(0, h))
        self.speed = rng.uniform(6, 18)  # rows per second
        self.length = rng.randint(5, max(6, h // 2))


class Matrix:
    fps = 12

    def __init__(self, s, side, label=None):
        self.s = s
        self.rng = random.Random()
        self.label = label
        self.last = time.time()
        self.resize()

    def resize(self):
        s, rng = self.s, self.rng
        # one drop per column, staggered so the first frame isn't empty
        self.drops = [Drop(s.h, rng, start=rng.randint(-s.h, s.h)) for _ in range(s.w)]
        self.cells = [[rng.choice(GLYPHS) for _ in range(s.w)] for _ in range(s.h)]
        if self.label:
            pixels, bh, bw = block_text(self.label, s.w - 4)
            y0, x0 = max(0, (s.h - bh) // 2), max(0, (s.w - bw) // 2)
            self.pixels = {(y + y0, x + x0): i for (y, x), i in pixels.items()}
            # the block plus a margin; rain flows behind it
            self.box = (y0 - 1, y0 + bh, x0 - 2, x0 + bw + 1)
            self.scramble = [0.0] * len(self.label)  # seconds left scrambling, per letter

    def in_label_box(self, y, x):
        if not self.label:
            return False
        top, bottom, left, right = self.box
        return top <= y <= bottom and left <= x <= right

    def frame(self, now):
        s, rng = self.s, self.rng
        dt, self.last = now - self.last, now

        # glyphs shimmer in place, like the film
        for _ in range(max(1, s.w * s.h // 60)):
            self.cells[rng.randrange(s.h)][rng.randrange(s.w)] = rng.choice(GLYPHS)

        for x, d in enumerate(self.drops):
            d.y += d.speed * dt
            if d.y - d.length > s.h:
                self.drops[x] = Drop(s.h, rng)
                continue
            head = int(d.y)
            for i in range(d.length):
                y = head - i
                if y < 0 or y >= s.h or self.in_label_box(y, x):
                    continue
                if i == 0:
                    s.put(y, x, self.cells[y][x], curses.COLOR_WHITE, curses.A_BOLD)
                elif i < d.length // 3:
                    s.put(y, x, self.cells[y][x], curses.COLOR_GREEN, curses.A_BOLD)
                else:
                    s.put(y, x, self.cells[y][x], curses.COLOR_GREEN)

        if self.label:
            for i in range(len(self.label)):
                if self.scramble[i] <= 0 and rng.random() < 0.004:
                    self.scramble[i] = rng.uniform(0.3, 1.2)
                elif self.scramble[i] > 0:
                    self.scramble[i] -= dt
            # a scrambling letter dissolves into glyphs, then snaps back to blocks
            for (y, x), i in self.pixels.items():
                if self.scramble[i] > 0:
                    s.put(y, x, rng.choice(GLYPHS), curses.COLOR_GREEN, curses.A_BOLD)
                else:
                    s.put(y, x, "█", curses.COLOR_GREEN, curses.A_BOLD)  # █


# ---------------------------------------------------------------- sysrain

SYS_COLORS = {"cpu": curses.COLOR_RED, "mem": curses.COLOR_CYAN,
              "net": curses.COLOR_YELLOW, "gpu": curses.COLOR_MAGENTA}
LINUX = sys.platform.startswith("linux")


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def human(n):
    for unit in ("", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit in ("", "K") else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


class Sampler:
    """Polls the system every PERIOD seconds and turns activity into
    (category, text) tokens; busier categories produce more tokens."""
    PERIOD = 2.0

    def __init__(self):
        self.queue = collections.deque(maxlen=60)  # small: stays current, backlog = pressure
        self.stats = {}  # category -> short string for the footer
        self.prev_ticks, self.prev_rss, self.prev_net = {}, {}, None
        self.ncpu = os.cpu_count() or 1
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            t = time.time()
            try:
                self.sample(t)
            except Exception:  # a probe broke on this platform: keep raining
                pass
            time.sleep(max(0.2, self.PERIOD - (time.time() - t)))

    def procs(self, dt):
        """[(name, cpu_percent, rss_bytes)]"""
        out = []
        if LINUX:  # ps %cpu is a lifetime average on Linux, so diff /proc ticks
            hz, page = os.sysconf("SC_CLK_TCK"), os.sysconf("SC_PAGE_SIZE")
            ticks = {}
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                try:
                    with open(f"/proc/{pid}/stat") as f:
                        raw = f.read()
                except OSError:
                    continue
                name = raw[raw.index("(") + 1:raw.rindex(")")]
                fields = raw[raw.rindex(")") + 2:].split()
                ticks[pid] = int(fields[11]) + int(fields[12])
                cpu = (ticks[pid] - self.prev_ticks.get(pid, ticks[pid])) / hz / dt * 100
                out.append((name, cpu, int(fields[21]) * page))
            self.prev_ticks = ticks
        else:
            for line in run("ps", "-Ao", "pcpu=,rss=,comm=").splitlines():
                parts = line.split(None, 2)
                if len(parts) == 3:
                    out.append((os.path.basename(parts[2]), float(parts[0]), int(parts[1]) * 1024))
        return out

    def mem_pressure(self):
        if LINUX:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k] = int(v.split()[0])
            return 1 - info["MemAvailable"] / info["MemTotal"]
        m = re.search(r"free percentage: (\d+)%", run("memory_pressure", "-Q"))
        return 1 - int(m.group(1)) / 100 if m else 0.0

    def net_bytes(self):
        total = 0
        if LINUX:
            with open("/proc/net/dev") as f:
                for line in list(f)[2:]:
                    iface, data = line.split(":", 1)
                    if iface.strip() != "lo":
                        v = data.split()
                        total += int(v[0]) + int(v[8])
        else:
            for line in run("netstat", "-ib").splitlines()[1:]:
                p = line.split()
                if len(p) > 6 and p[2].startswith("<Link") and not p[0].startswith("lo"):
                    total += int(p[-5]) + int(p[-2])  # Ibytes, Obytes
        return total

    def peers(self):
        out = []
        if LINUX:
            for line in run("ss", "-tn", "state", "established").splitlines()[1:]:
                p = line.split()
                if len(p) >= 4:
                    out.append(p[3].rsplit(":", 1)[0].strip("[]"))
        else:
            for line in run("netstat", "-anp", "tcp").splitlines():
                p = line.split()
                if len(p) >= 6 and p[5] == "ESTABLISHED":
                    out.append(p[4].rsplit(".", 1)[0])
        return [a for a in out if not a.startswith(("127.", "::1"))]

    def gpu_util(self):
        if LINUX:
            vals = []
            for path in glob.glob("/sys/class/drm/card*/device/gpu_busy_percent"):
                try:
                    with open(path) as f:
                        vals.append(int(f.read()))
                except (OSError, ValueError):
                    pass
            return max(vals) if vals else None
        m = re.search(r'"Device Utilization %"=(\d+)', run("ioreg", "-r", "-d", "1", "-c", "IOAccelerator"))
        return int(m.group(1)) if m else None

    def sample(self, now):
        q, rng = self.queue, random
        dt = self.PERIOD
        procs = self.procs(dt)

        # cpu: processes drip their names at an average of 1 token per 50% of
        # a core per sample (fractions are rolled), max 3, so a process idling
        # at 15% shows up every few samples and a pegged one every sample
        cpu_total = sum(c for _, c, _ in procs) / self.ncpu
        for name, cpu, _ in sorted(procs, key=lambda p: -p[1])[:8]:
            n = cpu / 50
            n = int(n) + (rng.random() < n - int(n))
            q.extend([("cpu", name)] * min(3, n))
        self.stats["cpu"] = f"{cpu_total:.0f}%"

        # mem: processes that grew, plus big residents once pressure passes 50%
        pressure = self.mem_pressure()
        rss = {name: r for name, _, r in procs}
        for name, r in rss.items():
            grew = r - self.prev_rss.get(name, r)
            if grew > 16 * 2**20:
                q.append(("mem", f"{name} +{human(grew)}"))
        self.prev_rss = rss
        big = sorted(procs, key=lambda p: -p[2])[:12]
        for _ in range(round(max(0.0, pressure - 0.5) * 12)):  # only under real pressure
            name, _, r = rng.choice(big)
            q.append(("mem", f"{name} {human(r)}"))
        self.stats["mem"] = f"{pressure * 100:.0f}%"

        # net: throughput sets how many tokens (log scale); live peers are what they say
        nb = self.net_bytes()
        rate = 0 if self.prev_net is None else max(0, nb - self.prev_net) / dt
        self.prev_net = nb
        peers = self.peers()
        for _ in range(round(math.log10(1 + rate / 50e3) * 2)):  # ~0 below 50K/s, 3 at 1M/s
            q.append(("net", rng.choice(peers) if peers else f"{human(rate)}/s"))
        self.stats["net"] = f"{human(rate)}/s"

        # gpu: utilization only (no per-process view without root)
        g = self.gpu_util()
        if g is not None:
            q.extend([("gpu", f"GPU {g}%")] * round(g / 15))
            self.stats["gpu"] = f"{g}%"


MAX_WORDS_PER_SEC = 2.5


class SysRain:
    """Matrix rain over a grid of system activity. Like the film, glyphs sit
    still and falling drops light them up. Every bit of activity becomes a
    token in a queue; each token is planted into the grid as a horizontal word
    at a random spot (for WORD_LIFE seconds) and a shower of drops, one per
    letter, falls through it; revealed words glow for GLOW seconds. Planting rate tracks queue size, so density is
    pressure. Revealed words: cpu red, mem cyan, net yellow, gpu magenta;
    plain katakana is ambient."""
    fps = 12
    WORD_LIFE = 30.0
    GLOW = 4.0  # seconds a revealed word stays lit

    def __init__(self, s, side):
        self.s = s
        self.rng = random.Random()
        self.sampler = Sampler()
        self.drops = []  # [x, head_y, speed, trail_len]
        self.last = time.time()
        self.debt = 0.0
        self.resize()

    def resize(self):
        s, rng = self.s, self.rng
        # each cell: [glyph, color or None, expiry, glow_until]
        self.cells = [[[rng.choice(GLYPHS), None, 0.0, 0.0] for _ in range(s.w)] for _ in range(s.h)]

    def plant(self, now, cat, text):
        """Write the token horizontally at a random spot and send a shower --
        one drop per letter, slightly staggered -- down through it."""
        s, rng = self.s, self.rng
        text = text[: s.w]
        for _ in range(8):  # find a spot that doesn't overwrite a live word
            x0, y = rng.randrange(0, max(1, s.w - len(text) + 1)), rng.randrange(0, max(1, s.h - 1))
            row = self.cells[y][x0:x0 + len(text)]
            if all(c[1] is None or c[2] < now for c in row):
                break
        else:
            return
        start, speed = float(-rng.randint(2, 8)), rng.uniform(7, 11)
        for i, ch in enumerate(text):
            self.cells[y][x0 + i] = [ch, SYS_COLORS[cat], now + self.WORD_LIFE, 0.0]
            self.drops.append([x0 + i, start - rng.uniform(0, 1.5), speed * rng.uniform(0.9, 1.1), rng.randint(3, 7)])

    def frame(self, now):
        s, rng, q = self.s, self.rng, self.sampler.queue
        dt, self.last = now - self.last, now

        # plant rate tracks the backlog (density = pressure), capped so a busy
        # box is a downpour of readable words, not a wall of them
        self.debt += dt * min(MAX_WORDS_PER_SEC, len(q) / 6)
        while self.debt >= 1 and q:
            self.debt -= 1
            self.plant(now, *q.popleft())
        if not q:
            self.debt = 0.0
        if rng.random() < dt * 1.2:
            self.drops.append([rng.randrange(s.w), float(-rng.randint(0, 10)), rng.uniform(7, 14), rng.randint(6, 18)])

        # unplanted glyphs shimmer; expired words dissolve back into katakana
        for _ in range(max(1, s.w * s.h // 80)):
            c = self.cells[rng.randrange(s.h)][rng.randrange(s.w)]
            if c[1] is None or c[2] < now:
                c[0], c[1], c[3] = rng.choice(GLYPHS), None, 0.0

        alive = []
        for d in self.drops:
            d[1] += d[2] * dt
            x, head, _, trail = d
            head = int(head)
            if head - trail >= s.h - 1:
                continue
            alive.append(d)
            for i in range(trail):
                y = head - i
                if not 0 <= y < s.h - 1 or x >= s.w:
                    continue
                cell = self.cells[y][x]
                ch, color, expiry = cell[0], cell[1], cell[2]
                if color is not None and expiry >= now:
                    cell[3] = now + self.GLOW  # a lit word keeps glowing after the drop passes
                if i == 0:
                    s.put(y, x, ch, curses.COLOR_WHITE, curses.A_BOLD)
                elif color is not None and expiry >= now:
                    s.put(y, x, ch, color, curses.A_BOLD)
                else:
                    s.put(y, x, ch, curses.COLOR_GREEN, curses.A_BOLD if i < trail // 3 else (0 if i < 2 * trail // 3 else curses.A_DIM))
        self.drops = alive

        # afterglow: lit words fade bold -> normal -> dim, drawn over the rain
        for y, row in enumerate(self.cells[: s.h - 1]):
            for x, (ch, color, expiry, glow) in enumerate(row):
                if color is not None and glow > now and expiry >= now:
                    left = (glow - now) / self.GLOW
                    s.put(y, x, ch, color, curses.A_BOLD if left > 0.6 else (0 if left > 0.25 else curses.A_DIM))

        # footer legend, in the words' colors
        x = 1
        for cat in ("cpu", "mem", "net", "gpu"):
            if cat in self.sampler.stats:
                label = f"{cat} {self.sampler.stats[cat]} "
                s.put(s.h - 1, x, label, SYS_COLORS[cat])
                x += len(label)


# ---------------------------------------------------------------- transit

MBTA = "https://api-v3.mbta.com"
LINE_COLORS = {"Red": curses.COLOR_RED, "Mattapan": curses.COLOR_RED, "Orange": curses.COLOR_YELLOW,
               "Blue": curses.COLOR_BLUE, "Green": curses.COLOR_GREEN}
POLL = 20  # seconds between vehicle fetches (MBTA's keyless rate limit is modest)


def mbta(path):
    with urllib.request.urlopen(MBTA + path, timeout=10) as r:
        return json.load(r)


# Singapore MRT, schedule-shaped ("pseudo-live"): LTA publishes no live train
# positions, so trains run on a headway model by time of day. Station lists
# are typed from memory (Oct 2026) -- LTA's GTFS Schedule (Train) feed would
# be the authoritative upgrade.
SG_LINES = {
    "NSL": (curses.COLOR_RED, [
        "Jurong East", "Bukit Batok", "Bukit Gombak", "Choa Chu Kang", "Yew Tee", "Kranji", "Marsiling",
        "Woodlands", "Admiralty", "Sembawang", "Canberra", "Yishun", "Khatib", "Yio Chu Kang", "Ang Mo Kio",
        "Bishan", "Braddell", "Toa Payoh", "Novena", "Newton", "Orchard", "Somerset", "Dhoby Ghaut",
        "City Hall", "Raffles Place", "Marina Bay", "Marina South Pier"], None),
    "EWL": (curses.COLOR_GREEN, [
        "Pasir Ris", "Tampines", "Simei", "Tanah Merah", "Bedok", "Kembangan", "Eunos", "Paya Lebar",
        "Aljunied", "Kallang", "Lavender", "Bugis", "City Hall", "Raffles Place", "Tanjong Pagar",
        "Outram Park", "Tiong Bahru", "Redhill", "Queenstown", "Commonwealth", "Buona Vista", "Dover",
        "Clementi", "Jurong East", "Chinese Garden", "Lakeside", "Boon Lay", "Pioneer", "Joo Koon",
        "Gul Circle", "Tuas Crescent", "Tuas West Road", "Tuas Link"], ("Tanah Merah", ["Expo", "Changi Airport"])),
    "NEL": (curses.COLOR_MAGENTA, [
        "HarbourFront", "Outram Park", "Chinatown", "Clarke Quay", "Dhoby Ghaut", "Little India",
        "Farrer Park", "Boon Keng", "Potong Pasir", "Woodleigh", "Serangoon", "Kovan", "Hougang",
        "Buangkok", "Sengkang", "Punggol", "Punggol Coast"], None),
}
SG_DWELL = 30  # seconds stopped at each station


def sg_run(a, b):
    """Running time between adjacent stations, 90-170 s: fixed per station pair
    (crc32, not hash(), so both spacer processes agree)."""
    return 90 + zlib.crc32(("|".join(sorted((a, b)))).encode()) % 81


def sg_headway(t):
    """Seconds between trains at SGT clock time t (epoch seconds)."""
    lt = time.gmtime(t + 8 * 3600)
    hm = lt.tm_hour + lt.tm_min / 60
    peak = lt.tm_wday < 5 and (7 <= hm < 9.5 or 17 <= hm < 20)
    return 150 if peak else (420 if hm >= 22 or hm < 7 else 300)


def sg_trains(stops, now):
    """Trains on a line as (station, direction, status), from a deterministic
    timetable: departures from each end every sg_headway() between 05:30 and
    23:45 SGT (the reverse direction offset by a fraction of a headway)."""
    day0 = (now + 8 * 3600) // 86400 * 86400 - 8 * 3600  # SGT midnight
    trains = []
    for d in (0, 1):
        order = stops if d == 0 else stops[::-1]
        arrive = [0.0]  # arrival time at each station, relative to departure
        for x, y in zip(order, order[1:]):
            arrive.append(arrive[-1] + SG_DWELL + sg_run(x, y))
        for start in (day0 - 86400, day0):  # yesterday's late trains may still be running
            dep = start + 5.5 * 3600 + d * 97
            while dep <= start + 23.75 * 3600 and dep <= now:
                e = now - dep
                if e < arrive[-1] + SG_DWELL:
                    i = max(j for j, t in enumerate(arrive) if t <= e)
                    if e - arrive[i] < SG_DWELL or i == len(order) - 1:
                        trains.append((order[i], d, "STOPPED_AT"))
                    else:
                        trains.append((order[i + 1], d, "IN_TRANSIT_TO"))
                dep += sg_headway(dep)
    return trains


class Transit:
    """Transit line diagram. @zen-transit picks the lines, e.g. "Red,Orange"
    or "sg:NSL,EWL" (a system prefix carries forward; default mbta): the left
    spacer shows the first, the right the second. MBTA is live; sg is
    schedule-shaped (see SG_LINES). Stations run top to
    bottom (direction 0); a second branch (Red: Braintree vs Ashmont) forks
    off to its own column. Trains: v heading down the page, ^ heading up."""
    fps = 1

    def __init__(self, s, side):
        self.s = s
        lines, system = [], "mbta"
        for entry in (opt("zen-transit") or "Red,Orange").split(","):
            if ":" in entry:
                system, entry = entry.split(":", 1)
            if entry.strip():
                lines.append((system.strip().lower(), entry.strip()))
        self.system, self.route = lines[0] if side == "left" or len(lines) == 1 else lines[1]
        self.main, self.branch, self.fork = [], [], 0
        self.trains, self.updated, self.error = [], 0.0, ""
        if self.system == "sg":
            self.route = self.route.upper()
            self.color, self.main, branch = SG_LINES.get(self.route, (curses.COLOR_WHITE, ["(unknown line)"], None))
            if branch:
                self.fork, self.branch = self.main.index(branch[0]), branch[1]
        else:
            self.color = LINE_COLORS.get(self.route.split("-")[0], curses.COLOR_WHITE)
            threading.Thread(target=self.fetch_loop, daemon=True).start()

    def resize(self):
        pass

    def fetch_loop(self):
        q = urllib.parse.quote
        while True:
            try:
                if not self.main:
                    d = mbta(f"/route_patterns?filter[route]={q(self.route)}&filter[direction_id]=0"
                             "&include=representative_trip.stops&fields[stop]=name")
                    inc = {(i["type"], i["id"]): i for i in d.get("included", [])}
                    pats = []
                    for p in d["data"]:
                        if p["attributes"].get("typicality") != 1:
                            continue
                        trip = inc.get(("trip", p["relationships"]["representative_trip"]["data"]["id"]))
                        if trip:
                            pats.append([inc[("stop", st["id"])]["attributes"]["name"]
                                         for st in trip["relationships"]["stops"]["data"]])
                    pats.sort(key=len, reverse=True)
                    main = pats[0]
                    for other in pats[1:2]:  # one extra branch is all the column fits
                        i = next((i for i, (a, b) in enumerate(zip(main, other)) if a != b), len(other))
                        self.branch, self.fork = other[i:], i - 1
                    self.main = main
                d = mbta(f"/vehicles?filter[route]={q(self.route)}&include=stop&fields[stop]=name"
                         "&fields[vehicle]=current_status,direction_id")
                names = {i["id"]: i["attributes"]["name"] for i in d.get("included", [])}
                trains = []
                for v in d["data"]:
                    st = v["relationships"]["stop"]["data"]
                    if st and st["id"] in names:
                        a = v["attributes"]
                        trains.append((names[st["id"]], a["direction_id"], a["current_status"]))
                self.trains, self.updated, self.error = trains, time.time(), ""
            except Exception as e:  # network down, API change, rate limit: show it, keep going
                self.error = type(e).__name__
            time.sleep(POLL)

    def frame(self, now):
        s, color = self.s, self.color
        if self.system == "sg":
            self.trains = sg_trains(self.main, now)
            if self.branch:  # the branch runs as a shuttle from the fork station
                self.trains += sg_trains([self.main[self.fork]] + self.branch, now)
        s.put(0, 1, f"== {self.route.upper()} {'' if self.system == 'sg' else 'LINE '}==", color, curses.A_BOLD)
        if not self.main:
            s.put(2, 1, f"loading... {self.error}", curses.COLOR_WHITE, curses.A_DIM)
            return

        n = len(self.main) + len(self.branch)
        step = 2 if n * 2 <= s.h - 4 else 1
        col_a, col_b = 6, 2
        rows = {}  # station name -> (row, track column)
        for i, name in enumerate(self.main):
            rows[name] = (2 + i * step, col_a)
        for j, name in enumerate(self.branch):
            rows.setdefault(name, (2 + (len(self.main) + j) * step, col_b))

        # tracks: the trunk, and the branch forking off left from the shared stop
        top, bottom = rows[self.main[0]][0], rows[self.main[-1]][0]
        for y in range(top, bottom + 1):
            s.put(y, col_a, "┃", color, curses.A_BOLD)  # ┃
        if self.branch:
            fy = rows[self.main[self.fork]][0]
            s.put(fy, col_b, "┏" + "━" * (col_a - col_b - 1), color, curses.A_BOLD)  # ┏━
            for y in range(fy + 1, rows[self.branch[-1]][0] + 1):
                s.put(y, col_b, "┃", color, curses.A_BOLD)

        ends = {self.main[0], self.main[-1]} | ({self.branch[-1]} if self.branch else set())
        for name, (y, c) in rows.items():
            s.put(y, c, "o", curses.COLOR_WHITE, curses.A_BOLD)
            s.put(y, c + 3, name[: max(0, s.w - c - 4)], curses.COLOR_WHITE, curses.A_BOLD if name in ends else 0)

        for name, direction, status in self.trains:
            if name not in rows:
                continue
            y, c = rows[name]
            if status != "STOPPED_AT" and step == 2:
                y += -1 if direction == 0 else 1  # between the previous station and this one
            if direction == 0:
                s.put(y, c - 1, "v", color, curses.A_BOLD | curses.A_REVERSE)
            else:
                s.put(y, c + 1, "^", color, curses.A_BOLD | curses.A_REVERSE)

        if self.system == "sg":
            footer = f"{len(self.trains)} trains, {time.strftime('%H:%M', time.gmtime(now + 8 * 3600))} SGT (sched)"
        elif self.error and not self.updated:
            footer = f"offline ({self.error})"
        else:
            footer = f"{len(self.trains)} trains, {int(now - self.updated)}s ago" + (" (stale)" if self.error else "")
        s.put(s.h - 1, 1, footer[: s.w - 2], curses.COLOR_WHITE, curses.A_DIM)


# ---------------------------------------------------------------- main

def main(scr, style, side):
    curses.curs_set(0)
    curses.use_default_colors()
    for c in range(8):
        curses.init_pair(c + 1, c, -1)
    scr.nodelay(True)
    global PIXELS
    PIXELS = opt("zen-pixels") if opt("zen-pixels") in ("octant", "mixed") else "braille"

    s = Screen(scr)
    if style == "garden":
        scene = Garden(s, side)
    elif style == "sysrain":
        scene = SysRain(s, side)
    elif style == "transit":
        scene = Transit(s, side)
    elif style == "coffee":
        scene = Coffee(s, side)
    elif style == "matrix":
        scene = Matrix(s, side)
    elif style in ("gallery", "gallery-color"):  # gallery-color: old name, kept working
        scene = Gallery(s, side)
    elif style == "ink":
        scene = Ink(s, side)
    elif style == "host":
        # host on the left, user on the right: MONST3R | (your work) | AVASHEVKO
        if side == "left":
            label = socket.gethostname().split(".")[0]
        else:
            label = getpass.getuser()
        scene = Matrix(s, side, label=label.upper())
    else:
        raise SystemExit(f"zen-spacer: unknown style {style!r}")

    pane = os.environ.get("TMUX_PANE", "")
    # one tmux call a second: respawn when the style options change, re-center
    # when the width does, and pause while no client can see this window
    # (client_theme: tmux's read of the terminal going light/dark, e.g. an
    # ansil16 switch; a respawn re-asks the terminal for its colours)
    fmt = "#{@zen-style}|#{@zen-spacer}|#{@zen-pixels}|#{@zen-gallery-palette}|#{client_theme}\t#{@zen-width}|#{window_width}\t#{window_id}|#{window_zoomed_flag}"

    def poll():
        return (tmux("display", "-p", "-t", pane, fmt).split("\t") + ["", ""])[:3]
    watched, fitted, _ = poll() if pane else ("", "", "")
    visible, next_check = True, time.time() + 1
    while True:
        key = scr.getch()
        if key in (ord("q"), 4):
            return
        if key == curses.KEY_RESIZE:
            s.resize()
            scene.resize()
        if pane and time.time() >= next_check:
            next_check = time.time() + 1
            style, fit, win = poll()
            if style != watched:
                # run in the server, not as our child: respawn-pane kills us
                tmux("run-shell", "-b", f"'{HERE}/zen.sh' respawn '{pane}' '{side}' '{os.environ.get('ZEN_CENTER', '')}' '{os.environ.get('ZEN_SEED', '0')}'")
                time.sleep(5)
            # the left spacer also keeps the center at @zen-width (fit sizes both)
            if side == "left" and fit != fitted:
                fitted = fit
                tmux("run-shell", "-b", f"'{HERE}/zen.sh' fit '{pane}'")
            # visible = some attached client is on this window and it isn't
            # zoomed. A tmux nested over ssh can't tell when the outer one
            # hides it, so it just keeps animating.
            wid, _, zoomed = win.partition("|")
            visible = zoomed != "1" and wid in tmux("list-clients", "-F", "#{window_id}").split()
        if not visible:
            # scenes are drawn from the clock, so they resume where they'd be
            time.sleep(0.5)
            continue
        scr.erase()
        scene.frame(time.time())
        s.refresh()
        if pane and getattr(scene, "respawn", False):
            tmux("run-shell", "-b", f"'{HERE}/zen.sh' respawn '{pane}' '{side}' '{os.environ.get('ZEN_CENTER', '')}' '{os.environ.get('ZEN_SEED', '0')}'")
            time.sleep(5)
        time.sleep(1 / scene.fps)


TERM_BG = None      # the terminal's background (linear rgb), asked at startup
TERM_PALETTE = {}   # its 16 colours, index -> linear rgb


def query_colors(timeout=0.6):
    """Ask the terminal for its background (OSC 11) and 16 colours (OSC 4).
    tmux answers for its client, so this sees colours set at runtime (e.g. by
    ansil16 through kitty), even over ssh. Before curses starts; best effort."""
    global TERM_BG
    try:
        import termios
        import tty
        import select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
    except (ImportError, OSError, ValueError):
        return
    try:
        tty.setraw(fd)
        os.write(1, b"\033]11;?\033\\" + b"".join(b"\033]4;%d;?\033\\" % i for i in range(16)))
        buf, end = b"", time.time() + timeout
        while time.time() < end and buf.count(b"rgb:") < 17:
            if select.select([fd], [], [], 0.05)[0]:
                buf += os.read(fd, 1024)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def rgb(m):
        return tuple(srgb_lin(int(h, 16) / (16 ** len(h) - 1) * 255) for h in m)
    for m in re.finditer(rb"\]11;rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", buf):
        TERM_BG = rgb(g.decode() for g in m.groups())
    for m in re.finditer(rb"\]4;(\d+);rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", buf):
        TERM_PALETTE[int(m.group(1))] = rgb(g.decode() for g in m.groups()[1:])


if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "garden"
    query_colors()
    try:
        curses.wrapper(main, style, os.environ.get("ZEN_SIDE", "left"))
    except KeyboardInterrupt:
        pass
