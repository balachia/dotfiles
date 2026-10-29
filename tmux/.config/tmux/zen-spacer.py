#!/usr/bin/env python3
# stdlib only, on purpose: runs on whatever system python3 is around.
"""zen-spacer: animated spacer panes for zen.sh.

Usage: zen-spacer.py <style>   (ZEN_SIDE=left|right is set by zen.sh)

Styles:
  garden  leaves on the wind over grass and flowers, drawn as one
          window-wide scene: leaves blow behind the center pane and come
          out the other side.
  coffee  a table across both panels: a steaming mug with the hostname on
          it on one side, a green banker's lamp under an analog wall clock, both in braille, on the other (side picked at random per
          toggle). The coffee goes cold after 45 minutes.
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
import glob
import getpass
import json
import math
import os
import random
import re
import socket
import subprocess
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


class Screen:
    def __init__(self, scr):
        self.scr = scr
        self.resize()

    def resize(self):
        self.h, self.w = self.scr.getmaxyx()
        # where this pane sits in the window, for window-wide ("world") scenes
        geo = tmux("display", "-p", "-t", os.environ.get("TMUX_PANE", ""), "#{pane_left} #{window_width}").split()
        self.x0, self.world_w = (int(geo[0]), int(geo[1])) if len(geo) == 2 else (0, self.w)

    def put(self, y, x, s, color, attr=0):
        # skip the bottom-right cell: writing there makes curses raise
        if 0 <= y < self.h and 0 <= x < self.w and not (y == self.h - 1 and x == self.w - 1):
            try:
                self.scr.addstr(y, x, s, curses.color_pair(color + 1) | attr)
            except curses.error:
                pass


# ---------------------------------------------------------------- garden

LEAF_GLYPHS = ",'`~"
LEAF_COLORS = [curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_RED, curses.COLOR_MAGENTA]
FLOWER_HEADS = "*@o✿"  # ✿
FLOWER_COLORS = [curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_WHITE]


GUST_PERIOD = 20.0


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


SLOT = 0.5          # a leaf may launch from the window's left edge every SLOT seconds
LEAF_LIFE = 150.0   # older leaves are dropped (both panels apply the same cutoff)


class Garden:
    """Window-wide landscape in depth layers, back to front: clouds, far
    mountains, mid hills with trees, far leaves, near grass/flowers/leaves.
    Far things are dimmer and move slower."""
    fps = 5

    def __init__(self, s, side):
        self.s = s
        self.resize()

    def resize(self):
        # the flower bed is laid out across the whole window, so it lines up
        # on both sides of the center pane
        rng = random.Random(7)
        self.bed = []
        x = rng.randrange(1, 5)
        while x < self.s.world_w - 1:
            self.bed.append((x, rng.randint(2, 4), rng.choice(FLOWER_HEADS), rng.choice(FLOWER_COLORS)))
            x += rng.randint(4, 9)

        # mountains (far, tall, steep) and hills (mid, low, gentle)
        h = self.s.h
        self.ranges = {}
        for layer, base, lo, hi, gap, slope in (("far", 0.50, 0.18, 0.40, (8, 20), (0.6, 1.0)),
                                                ("mid", 0.72, 0.62, 0.68, (14, 30), (0.25, 0.4))):
            peaks, px = [], rng.randint(-10, 5)
            while px < self.s.world_w + 20:
                peaks.append((px, rng.uniform(h * lo, h * hi), rng.uniform(*slope)))
                px += rng.randint(*gap)
            self.ranges[layer] = (h * base, peaks)

    def leaves(self, now, depth, salt, y_lo, y_hi):
        """Every live leaf in one depth layer as (world_x, y, k); identical in
        both panels. depth scales speed (far = slow)."""
        for k in range(int((now - LEAF_LIFE) // SLOT), int(now // SLOT) + 1):
            t0 = k * SLOT
            r = random.Random(k * 7919 + salt)
            if r.random() > 0.25 * wind(t0) or t0 > now:
                continue
            y0, vy = r.uniform(y_lo, y_hi * 0.75), r.uniform(0.15, 0.6) * depth
            phase, speed = r.uniform(0, 6.28), r.uniform(0.6, 1.2) * depth
            x = -1 + 6.0 * speed * wind_travel(t0, now)
            # vertical: steady fall plus the integral of a sin(1.7t) flutter
            amp = 0.5 * depth
            y = y0 + vy * (now - t0) + (amp / 1.7) * (math.cos(1.7 * t0 + phase) - math.cos(1.7 * now + phase))
            if x >= self.s.world_w or y >= y_hi:
                continue
            yield x, y, r, phase

    def ridge(self, layer, wx):
        """Row of a ridge line at world column wx: the highest of a row of
        triangular peaks, laid out once per window width (same in both panels)."""
        base, peaks = self.ranges[layer]
        return min([base] + [py + abs(wx - px) * slope for px, py, slope in peaks])

    def draw_ridge(self, layer, color, attr):
        s = self.s
        for x in range(s.w):
            wx = s.x0 + x
            y, yl, yr = (int(self.ridge(layer, v)) for v in (wx, wx - 1, wx + 1))
            if y < yl and y < yr:
                ch = "^"
            elif yr < y:
                ch = "/"
            elif yr > y:
                ch = "\\"
            else:
                ch = "_"
            s.put(y, x, ch, color, attr)
            for fill in range(min(yl, yr) + 1, y):  # close gaps on steep slopes
                s.put(fill, x, "|", color, attr)
            # a sparse forest on the near hills
            if layer == "mid" and random.Random(wx * 31).random() < 0.12:
                s.put(y - 1, x, "^", curses.COLOR_GREEN)

    def frame(self, now):
        s = self.s
        wd = wind(now)

        # clouds: slow drift across the whole window
        period = s.world_w + 30
        for k in range(max(2, s.world_w // 40)):
            cx = int((k * period / max(2, s.world_w // 40) + now * 0.4) % period) - 15 - s.x0
            cy = 1 + (k * 5) % max(1, s.h // 5)
            for i, line in enumerate(CLOUD):
                for j, ch in enumerate(line):
                    if ch != " ":
                        s.put(cy + i, cx + j, ch, curses.COLOR_WHITE, curses.A_DIM)

        self.draw_ridge("far", curses.COLOR_BLUE, curses.A_DIM)
        self.draw_ridge("mid", curses.COLOR_GREEN, curses.A_DIM)

        # far leaves: small, dim, slow, up high
        for wx, y, r, phase in self.leaves(now, 0.45, 1, 0, s.h * 0.7):
            s.put(int(y), int(wx) - s.x0, "." if int(now * 3 + phase) % 2 else "'", r.choice(LEAF_COLORS), curses.A_DIM)

        # grass: blades lean with the wind; the wave runs across the window
        for x in range(s.w):
            lean = wd + 0.35 * math.sin(now * 2.1 + (s.x0 + x) * 0.6)
            s.put(s.h - 1, x, "|" if lean < 0.6 else ("/" if lean < 1.2 else "_"), curses.COLOR_GREEN, curses.A_BOLD)

        # flowers: stem sways, head trails downwind in strong gusts
        for fx, fh, head, color in self.bed:
            x = fx - s.x0
            if not -2 <= x < s.w:
                continue
            lean = wd + 0.3 * math.sin(now * 1.3 + fx)
            for i in range(1, fh):
                sx = x + (1 if lean > 1.0 and i == fh - 1 else 0)
                s.put(s.h - 1 - i, sx, "/" if lean > 0.7 else "|", curses.COLOR_GREEN)
            hx = x + (1 if lean > 0.7 else 0) + (1 if lean > 1.2 else 0)
            s.put(s.h - 1 - fh, hx, head, color, curses.A_BOLD)

        # near leaves: big, bright, fast
        for wx, y, r, phase in self.leaves(now, 1.0, 0, 0, s.h - 1):
            s.put(int(y), int(wx) - s.x0, LEAF_GLYPHS[int(now * 5 + phase) % len(LEAF_GLYPHS)], r.choice(LEAF_COLORS))


CLOUD = ["   .--.    ", ".-(    ).  ", "(___.__)__)"]


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
    """A table across both panels; a steaming mug (with the hostname on it)
    on one side and a green banker's lamp under an analog wall clock, both in braille, on the other. The mug
    keeps real-mug proportions; the lamp scales with the panel. ZEN_SEED, shared by both spacers, picks which side
    gets the mug."""
    fps = 8

    def __init__(self, s, side):
        self.s = s
        seed = int(os.environ.get("ZEN_SEED", "0") or 0)
        self.mug = side == ("left" if seed % 2 == 0 else "right")
        self.name = " ".join(socket.gethostname().split(".")[0].upper())
        self.user = " ".join(getpass.getuser().upper())
        self.rng = random.Random()
        self.start = time.time()
        self.steam = []  # (born, x0, y0, phase), in braille dots
        self.last = self.start
        self.resize()

    def resize(self):
        h, w = self.s.h, self.s.w
        self.table_y = h - 4 if h >= 14 else h - 1
        self.cx = w // 2
        # mug: a fixed, real-mug size (fits the slogan); terminal cells are
        # ~2:1, so a mug about as tall as it is wide is ~0.45 rows per column.
        # Only shrinks when the panel is too narrow.
        widest = max(len(l) for l in self.slogan(MUG_SLOGANS[0])) + 6
        self.mw = clamp(widest, len(self.name) + 4, max(10, w - 6))
        self.mh = max(7, round(self.mw * 0.45))
        # lamp
        self.sw = clamp(w * 3 // 5, 15, 35) | 1
        # wall clock at the top: as wide as ~2/5 of the panel; cw cells wide is
        # cw/2 rows tall in braille. The lamp gets what's left below it.
        self.clock_cols = clamp(w * 2 // 5, 0, 24) // 2 * 2
        self.lh = clamp(h * 9 // 20, 10, max(10, self.table_y - self.clock_cols // 2 - 4))

    def slogan(self, lines):
        return [self.user if l == "USER" else self.name if l == "HOST" else l for l in lines]

    def mug_art(self):
        """The mug in box-drawing characters: rounded rim and base, and a
        handle joined to the body with tees."""
        mw, mh = self.mw, self.mh
        rows = ["\u256d" + "\u2500" * (mw - 2) + "\u256e",   # ╭──╮
                "\u2502" + "~" * (mw - 2) + "\u2502"]         # │~~│
        body = mh - 3
        h0, h1 = 1, max(3, body * 2 // 3)  # handle spans these body rows
        for i in range(body):
            if i == h0:
                side = "\u251c\u2500\u256e"   # ├─╮
            elif i == h1:
                side = "\u251c\u2500\u256f"   # ├─╯
            elif h0 < i < h1:
                side = "\u2502 \u2502"         # │ │
            else:
                side = "\u2502"
            rows.append("\u2502" + " " * (mw - 2) + side)
        rows.append("\u2570" + "\u2500" * (mw - 2) + "\u256f")  # ╰──╯
        return rows

    def art(self, y, x, lines, color, attr=0):
        for i, line in enumerate(lines):
            for j, ch in enumerate(line):
                if ch != " ":
                    self.s.put(y + i, x + j, ch, color, attr)

    def frame(self, now):
        s, ty = self.s, self.table_y
        dt, self.last = now - self.last, now

        # table: one line across both panels, wood grain below
        for x in range(s.w):
            s.put(ty, x, "_", curses.COLOR_YELLOW, curses.A_DIM)
            if (s.x0 + x) % 11 == 3:
                s.put(ty + 2, x, "~", curses.COLOR_YELLOW, curses.A_DIM)

        if self.mug:
            self.frame_mug(now, dt)
        else:
            self.frame_lamp(now)

    def frame_mug(self, now, dt):
        s, ty, mw = self.s, self.table_y, self.mw
        art = self.mug_art()
        mx = self.cx - (mw + 3) // 2
        top = ty - len(art)  # the mug sits just above the table row
        self.art(top, mx, art, curses.COLOR_WHITE, curses.A_BOLD)
        for j in range(1, mw - 1):
            s.put(top + 1, mx + j, "~", curses.COLOR_YELLOW)  # the coffee
        # printed on the mug: the first slogan that fits
        for slogan in MUG_SLOGANS:
            lines = self.slogan(slogan)
            if max(map(len, lines)) <= mw - 4 and len(lines) <= len(art) - 4:
                break
        y = top + 2 + (len(art) - 3 - len(lines)) // 2
        for i, (line, raw) in enumerate(zip(lines, slogan)):
            loud = raw in ("USER", "HOST")
            s.put(y + i, mx + (mw - len(line)) // 2, line,
                  curses.COLOR_RED if loud else curses.COLOR_WHITE, curses.A_BOLD if loud else 0)

        b = Braille()
        # saucer: a shallow braille dish in the table row, rim on top
        cxp, half = (mx + mw // 2) * 2, mw + 6
        for x in range(-half, half + 1):
            b.dot(cxp + x, ty * 4, (curses.COLOR_WHITE, curses.A_BOLD), 1)
            b.dot(cxp + x, ty * 4 + round(3 * (1 - (x / half) ** 2)), (curses.COLOR_WHITE, curses.A_BOLD), 1)

        # steam: braille wisps. Each puff is a short trail of dots along its
        # own curling path, fading as it rises.
        warmth = max(0.0, 1 - (now - self.start) / COLD_AFTER)
        if self.rng.random() < (0.6 + mw / 25) * warmth:
            self.steam.append((now, (mx + self.rng.uniform(2, mw - 2)) * 2, top * 4 - 1, self.rng.uniform(0, 6.28)))
        life = 4 + self.mh / 3
        self.steam = [p for p in self.steam if now - p[0] < life]
        for born, x0, y0, phase in self.steam:
            for back in range(6):  # the puff plus its trail
                age = now - born - back * 0.12
                if age < 0:
                    break
                x = x0 + 3 * math.sin(age * 1.8 + phase) + 1.0 * age
                y = y0 - 6.4 * age
                frac = age / life
                style = (curses.COLOR_WHITE, curses.A_BOLD if frac < 0.3 else (0 if frac < 0.65 else curses.A_DIM))
                b.dot(round(x), round(y), style, 2 - min(2, int(frac * 3)))
        b.render(s)

    def frame_lamp(self, now):
        s, ty, cx, sw = self.s, self.table_y, self.cx, self.sw
        y0 = max(1, ty - self.lh)  # top of the shade, in rows
        self.clock(now)

        # everything below is drawn in braille dots: x in [0, 2w), y in [0, 4h);
        # dots are square, so shapes keep their proportions
        b = Braille()
        glass, glass_edge = (curses.COLOR_GREEN, 0), (curses.COLOR_GREEN, curses.A_BOLD)
        brass, light = (curses.COLOR_YELLOW, 0), (curses.COLOR_YELLOW, curses.A_BOLD)
        cxp, half = cx * 2 + 1, sw  # shade half-width in dots (sw cells = 2*sw dots)
        top, depth = y0 * 4, 12  # shade: a dome, flat along the bottom
        bottom = top + depth

        for x in range(-half, half + 1):
            crown = top + round(depth * 0.55 * (x / half) ** 2)
            b.dot(cxp + x, crown, glass_edge, 2)
            b.dot(cxp + x, bottom, glass_edge, 2)
            for y in range(crown + 1, bottom):
                # ordered dither, denser toward the lit bottom edge
                if BAYER[y % 4][x % 4] < 2 + 12 * (y - crown) / max(1, bottom - crown):
                    b.dot(cxp + x, y, glass, 1)

        floor = ty * 4 + 3  # the table line is the bottom dot row of the table cells
        for x in range(-round(half * 1.6), round(half * 1.6) + 1):
            b.dot(cxp + x, floor, light, 3)  # lit pool on the table

        # base: a low brass dome; stem from the shade down into it
        bhalf, bh = max(6, half * 3 // 5), 6
        for x in range(-bhalf, bhalf + 1):
            rim = floor - 1 - round(bh * math.sqrt(max(0.0, 1 - (x / bhalf) ** 2)))
            b.dot(cxp + x, rim, light, 2)
            for y in range(rim + 1, floor):
                if BAYER[y % 4][x % 4] < 9:
                    b.dot(cxp + x, y, brass, 1)
        for y in range(bottom + 1, floor - bh):
            b.dot(cxp, y, light, 2)

        # pull chain: a pendulum hanging from the shade's edge
        px, py = cxp + half * 3 // 5, bottom + 1
        length = max(8, (floor - bottom) // 3)
        swing = 0.22 * math.sin(now * 1.1)
        for t in range(0, length, 2):
            b.dot(round(px + t * math.sin(swing)), round(py + t * math.cos(swing)), brass, 1)
        ex, ey = round(px + length * math.sin(swing)), round(py + length * math.cos(swing))
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            b.dot(ex + dx, ey + dy, light, 2)

        b.render(s)

    def clock(self, now):
        """Analog H:M wall clock at the top of the panel, on local time, in
        braille (square dots, so the face is a true circle)."""
        cw = self.clock_cols
        if cw < 8:
            return
        b = Braille()
        r = cw - 1  # radius in dots; the face is 2*cw dots = cw cells across
        cxp, cyp = (self.cx - cw // 2) * 2 + cw, 4 + cw  # center, one row down from the top
        rim, hour, minute = (curses.COLOR_WHITE, 0), (curses.COLOR_YELLOW, curses.A_BOLD), (curses.COLOR_WHITE, curses.A_BOLD)

        def line(style, rank, deg, r0, r1):
            th = math.radians(deg)
            steps = int((r1 - r0) * 2) + 1
            for i in range(steps + 1):
                t = r0 + (r1 - r0) * i / steps
                b.dot(round(cxp + t * math.sin(th)), round(cyp - t * math.cos(th)), style, rank)

        for i in range(360):
            th = math.radians(i)
            b.dot(round(cxp + r * math.sin(th)), round(cyp - r * math.cos(th)), rim, 0)
        for h in range(12):  # long ticks at 12/3/6/9, short ones between
            line(rim, 0, h * 30, r * (0.72 if h % 3 == 0 else 0.84), r - 1)
        lt = time.localtime(now)
        line(minute, 1, 6 * lt.tm_min, 0, r * 0.8)
        line(hour, 2, 30 * (lt.tm_hour % 12) + lt.tm_min / 2, 0, r * 0.5)
        b.render(self.s)


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]  # 4x4 ordered dither


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
            s.put(row, col, chr(0x2800 + bits), color, attr)



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
        for entry in (tmux("display", "-p", "#{@zen-transit}") or "Red,Orange").split(","):
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
    watched = tmux("display", "-p", "#{@zen-style}|#{@zen-spacer}")
    next_check = time.time() + 1
    while True:
        key = scr.getch()
        if key in (ord("q"), 4):
            return
        if key == curses.KEY_RESIZE:
            s.resize()
            scene.resize()
        if pane and time.time() >= next_check:
            next_check = time.time() + 1
            if tmux("display", "-p", "#{@zen-style}|#{@zen-spacer}") != watched:
                # run in the server, not as our child: respawn-pane kills us
                tmux("run-shell", "-b", f"'{HERE}/zen.sh' respawn '{pane}' '{side}' '{os.environ.get('ZEN_CENTER', '')}' '{os.environ.get('ZEN_SEED', '0')}'")
                time.sleep(5)
        scr.erase()
        scene.frame(time.time())
        scr.refresh()
        time.sleep(1 / scene.fps)


if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "garden"
    try:
        curses.wrapper(main, style, os.environ.get("ZEN_SIDE", "left"))
    except KeyboardInterrupt:
        pass
