#!/usr/bin/env python3
"""Fill ~/.cache/zen/gallery with public-domain paintings for the zen
"gallery" spacer style, from the Art Institute of Chicago's open API and IIIF
image server: small grayscale PNGs plus a caption each. Stdlib only.

  zen-gallery.py                  add a few random famous paintings (AIC highlights)
  zen-gallery.py --add 27992      add one artwork by AIC id
  zen-gallery.py --add "grande jatte"   ...or the best search hit
  zen-gallery.py --commons "school of athens raphael"   from Wikimedia Commons
                                  (public domain only; needs ImageMagick or sips)
  zen-gallery.py --plaques        top up each painting's takes (wall text + the
                                  critic's version) to 4 (LLM gateway, fact-checked)
  zen-gallery.py --if-stale 20    (for cron) do nothing if the last run was recent

Plaques: a cheap model writes a museum wall text and the same facts in the
voice of a fussy little critic; a second model from another vendor checks
them for accuracy, and only checked texts are kept (<id>.plaque.json). The
gateway and models are zen-slogans.py's.

Only artworks AIC marks is_public_domain are fetched. The spacer reads the
PNGs as data (dimensions are checked) and never runs anything from here.
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.artic.edu/api/v1"
IIIF = "https://www.artic.edu/iiif/2"
# AIC asks API clients to identify themselves; without a header Cloudflare
# answers with a browser challenge
HEADERS = {"AIC-User-Agent": "tmux-zen (personal terminal toy)", "User-Agent": "tmux-zen/0.1",
           "Accept": "application/json, image/png"}
CACHE = os.path.expanduser("~/.cache/zen/gallery")
STAMP = os.path.join(CACHE, "stamp")
KEEP = 40          # paintings kept on disk
PER_RUN = 3        # new random picks per run
WIDTH = 600        # pixels; a window is rarely more than ~500 braille dots wide
FIELDS = ["id", "title", "artist_title", "date_display", "image_id", "is_public_domain"]


def request(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(HEADERS, **({"Content-Type": "application/json"} if data else {}))
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def search(body):
    return json.loads(request(f"{API}/artworks/search", dict(body, fields=FIELDS)))["data"]


def random_paintings(n):
    """n random picks from AIC's highlighted ("boosted") public-domain
    paintings, about 120 famous ones, skipping any already cached. One request."""
    query = {"bool": {"must": [{"term": {"is_public_domain": True}},
                               {"term": {"artwork_type_id": 1}},       # 1 = Painting
                               {"term": {"is_boosted": True}},         # AIC's highlights
                               {"exists": {"field": "image_id"}}]}}
    have = {f[:-5] for f in os.listdir(CACHE) if f.endswith(".json")}
    pool = []
    for page in (1, 2):  # the API caps a page at 100
        pool += [a for a in search({"query": query, "limit": 100, "page": page}) if str(a["id"]) not in have]
    return random.sample(pool, min(n, len(pool)))


def lookup(term):
    if term.isdigit():
        return [json.loads(request(f"{API}/artworks/{term}?fields={','.join(FIELDS)}"))["data"]]
    return search({"q": term, "limit": 1})


def clean(s, n=80):
    return re.sub(r"[^\w .,;:'&()\-–—/]", "", " ".join(str(s or "").split()), flags=re.UNICODE)[:n]


def fetch(art):
    if not (art.get("is_public_domain") and art.get("image_id")):
        print(f"skip {art.get('id')}: not public domain or no image")
        return False
    aid = int(art["id"])
    png = request(f"{IIIF}/{art['image_id']}/full/{WIDTH},/0/gray.png")
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        print(f"skip {aid}: not a PNG")
        return False
    # a colour copy: the spacer picks an ink colour from it, or paints in it
    color = request(f"{IIIF}/{art['image_id']}/full/400,/0/default.png")
    meta = {"id": aid, "image_id": art["image_id"], "title": clean(art["title"]), "artist": clean(art.get("artist_title") or "Unknown"),
            "date": clean(art.get("date_display"), 40), "fetched": datetime.date.today().isoformat()}
    for name, data in ((f"{aid}.png", png), (f"{aid}-color.png", color), (f"{aid}.json", json.dumps(meta).encode())):
        tmp = os.path.join(CACHE, name + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(CACHE, name))
    print(f"added {aid}: {meta['artist']}, {meta['title']}, {meta['date']}")
    return True


COMMONS = "https://commons.wikimedia.org/w/api.php"
PD_LICENSES = ("public domain", "pd", "cc0")


def to_png(jpeg, width):
    """A downloaded JPEG as PNG bytes at width, via ImageMagick or macOS sips
    (the spacer only reads PNG: it's stdlib, and PNG is just zlib)."""
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "in.jpg"), os.path.join(tmp, "out.png")
        with open(src, "wb") as f:
            f.write(jpeg)
        if shutil.which("magick"):
            cmd = ["magick", src, "-resize", f"{width}x", "-strip", "-depth", "8", dst]
        elif shutil.which("convert"):
            cmd = ["convert", src, "-resize", f"{width}x", "-strip", "-depth", "8", dst]
        elif shutil.which("sips"):
            cmd = ["sips", "-s", "format", "png", "--resampleWidth", str(width), src, "--out", dst]
        else:
            raise OSError("no image converter: install ImageMagick")
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        with open(dst, "rb") as f:
            return f.read()


def strip_html(v):
    """Commons metadata is HTML with hidden Wikidata spans and every language:
    keep the English text if marked, drop hidden spans, then the tags."""
    v = str(v or "")
    en = re.search(r'lang="en"[^>]*>(.*?)</div>', v, flags=re.S)
    if en:  # its text, minus any edit-at-Wikidata link inside it
        return clean(re.sub(r"<[^>]+>", " ", re.sub(r"<span[^>]*noprint.*?</span>", "", en.group(1), flags=re.S)))
    v = re.sub(r'<(span|div)[^>]*display:\s*none.*?</\1>', "", v, flags=re.S)
    return clean(re.sub(r"<[^>]+>", " ", v))


def year(v):
    """The first year or year range in a Commons date field."""
    m = re.search(r"\b(1[0-9]{3}|20[0-9]{2})(\s*[-\u2013]\s*(1[0-9]{3}|20[0-9]{2}))?\b", re.sub(r"<[^>]+>", " ", str(v or "")))
    return m.group(0) if m else ""


def fetch_commons(query, pin):
    """Best public-domain file on Wikimedia Commons for query."""
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
              "gsrsearch": query, "gsrlimit": 8, "prop": "imageinfo",
              "iiprop": "url|extmetadata|mime", "iiurlwidth": WIDTH}
    data = json.loads(request(f"{COMMONS}?{urllib.parse.urlencode(params)}"))
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for page in pages:
        ii = (page.get("imageinfo") or [{}])[0]
        em = ii.get("extmetadata", {})
        lic = str(em.get("LicenseShortName", {}).get("value", "")).lower()
        if ii.get("mime") != "image/jpeg" or not lic.startswith(PD_LICENSES) or not ii.get("thumburl"):
            continue
        jpeg = request(ii["thumburl"])
        aid = f"c{page['pageid']}"
        # the title: English if the metadata marks it, else a quoted name in
        # the file name ('"The School of Athens" by ...'), else whatever is there
        raw = str(em.get("ObjectName", {}).get("value", ""))
        quoted = re.search(r'"([^"]+)"', page["title"])
        title = (strip_html(raw) if 'lang="en"' in raw else
                 clean(quoted.group(1)) if quoted else strip_html(raw) or page["title"][5:].rsplit(".", 1)[0])
        meta = {"id": aid, "title": title,
                "artist": strip_html(em.get("Artist", {}).get("value") or "Unknown"),
                "date": year(em.get("DateTimeOriginal", {}).get("value")),
                "source": "Wikimedia Commons", "fetched": datetime.date.today().isoformat()}
        save(aid, to_png(jpeg, WIDTH), to_png(jpeg, 400), meta, pin)
        return True
    print(f"no public-domain JPEG on Commons for {query!r}")
    return False


def save(aid, png, color, meta, pin=False):
    for name, data in ((f"{aid}.png", png), (f"{aid}-color.png", color), (f"{aid}.json", json.dumps(meta).encode())):
        tmp = os.path.join(CACHE, name + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(CACHE, name))
    if pin:
        open(os.path.join(CACHE, f"{aid}.pin"), "w").close()
    print(f"added {aid}: {meta['artist']}, {meta['title']}, {meta['date']}")


HERE = os.path.dirname(os.path.realpath(__file__))
PLAQUE_SYS = ("You write museum wall texts. Accuracy matters more than flourish: only "
              "well-established facts. Reply with one JSON object only.")
CHECK_SYS = ("You are a skeptical art historian fact-checking museum texts. Be strict: an "
             "invented detail, a wrong attribution, date, technique or provenance, or a "
             "description of something not in the painting is inaccurate. Reply with one JSON object only.")


VARIANTS = 4   # takes kept per painting, each looking at something different
ANGLES = ["one specific thing to look at in the composition",
          "the technique: brushwork, colour, surface",
          "the story or subject, and what it meant to its first viewers",
          "where it sits in the artist's life or the history of art"]


def plaques():
    """Top up each cached painting's takes to VARIANTS: a museum wall text and
    the same facts from the critic, each pair checked by the verifier."""
    zs = runpy.run_path(os.path.join(HERE, "zen-slogans.py"), run_name="zen_slogans")
    base = zs["gateway"]()
    if not base:
        print("plaques: no LLM gateway reachable; next run")
        return
    for path in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        if path.endswith(".plaque.json"):
            continue
        out_path = path[:-5] + ".plaque.json"
        try:
            with open(out_path) as f:
                have = json.load(f)
        except (OSError, ValueError):
            have = {}
        takes = have.get("takes") or ([{"plaque": have["plaque"], "critic": have["critic"]}]
                                      if have.get("plaque") else [])   # the one-take format
        if len(takes) >= VARIANTS:
            continue
        with open(path) as f:
            meta = json.load(f)
        about = f"Painting: {meta['title']}\nArtist: {meta['artist']}\nDate: {meta['date']}"
        angles = ANGLES[len(takes):VARIANTS]
        said = "".join(f"\n- {t['plaque']}" for t in takes)
        try:
            text, gen = zs["chat"](base, zs["GENERATOR"], PLAQUE_SYS, about + (
                f"\n\nWrite {len(angles)} takes on this painting, each about a different thing:\n"
                + "".join(f"{i + 1}. {a}\n" for i, a in enumerate(angles)) +
                (f"\nAlready said (don't repeat these points):{said}\n" if said else "") +
                "\nEach take is two texts, plain ASCII, each at most 300 characters:\n"
                '"plaque": museum wall text, two or three sentences. If you are not sure of '
                "facts about this particular work, speak about the artist's well-documented "
                "style instead.\n"
                '"critic": the same facts, spoken by a pompous but loving little art '
                "critic: fussy, a little vain, delighted, never cruel to the artist. Speak "
                "about the painting, not yourself: no stage directions, nothing about your "
                "clothes or gestures, and don't open with 'I'.\n"
                'Reply with a JSON array: [{"plaque": "...", "critic": "..."}, ...]'), 0.8)
            new = [{k: " ".join(str(t.get(k, "")).split())[:320] for k in ("plaque", "critic")}
                   for t in zs["json_array"](text) if isinstance(t, dict)]
            new = [t for t in new if t["plaque"] and t["critic"]][:len(angles)]
            if not new:
                print(f"plaques: {meta['id']}: no text")
                continue
            check, ver = zs["chat"](base, zs["VERIFIER"], CHECK_SYS, about + "\n\n" + "".join(
                f"Take {i + 1}a: {t['plaque']}\nTake {i + 1}b: {t['critic']}\n" for i, t in enumerate(new)) + (
                "\nFor each take, are both its texts factually accurate about this painting "
                'and artist? Reply: {"accurate": [true/false per take], "reason": "short"}'), 0.0, effort="low")
            verdict = zs["json_object"](check)
        except Exception as e:  # one painting failing shouldn't stop the rest
            print(f"plaques: {meta['id']}: {type(e).__name__}: {str(e)[:120]}")
            continue
        ok = verdict.get("accurate") if isinstance(verdict.get("accurate"), list) else []
        kept = [t for t, good in zip(new, ok) if good is True]
        if len(kept) < len(new):
            print(f"plaques: {meta['id']}: {len(new) - len(kept)} rejected: {str(verdict.get('reason', ''))[:140]}")
        if not kept:
            continue
        takes += kept
        with open(out_path + ".tmp", "w") as f:
            json.dump({"takes": takes, "generator": gen, "verifier": ver,
                       "date": datetime.date.today().isoformat()}, f)
        os.replace(out_path + ".tmp", out_path)
        print(f"plaques: {meta['id']}: {len(takes)} takes; new: {kept[-1]['critic'][:70]}...")


def prune():
    """Keep the newest KEEP; pinned paintings (a .pin file) are never dropped."""
    metas = sorted(((os.path.getmtime(os.path.join(CACHE, f)), f[:-5]) for f in os.listdir(CACHE)
                    if f.endswith(".json") and not f.endswith(".plaque.json")), reverse=True)
    for _, aid in metas[KEEP:]:
        if not os.path.exists(os.path.join(CACHE, aid + ".pin")):
            for ext in (".png", "-color.png", ".json", ".plaque.json"):
                try:
                    os.remove(os.path.join(CACHE, aid + ext))
                except OSError:
                    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--add", help="AIC artwork id or search terms")
    ap.add_argument("--commons", help="search Wikimedia Commons (public domain only)")
    ap.add_argument("--plaques", action="store_true", help="write missing plaques (LLM gateway)")
    ap.add_argument("--pin", action="store_true", help="with --add/--commons: never prune it")
    ap.add_argument("--if-stale", type=float, metavar="HOURS")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    if args.if_stale and os.path.exists(STAMP) and time.time() - os.path.getmtime(STAMP) < args.if_stale * 3600:
        return
    try:
        if args.plaques:
            plaques()
        elif args.commons:
            fetch_commons(args.commons, args.pin)
        elif args.add:
            for art in lookup(args.add):
                if fetch(art) and args.pin:
                    open(os.path.join(CACHE, f"{art['id']}.pin"), "w").close()
        else:
            added = 0
            for art in random_paintings(PER_RUN * 3):  # some images won't come back as PNG
                try:
                    added += fetch(art)
                except urllib.error.HTTPError as e:
                    print(f"skip {art.get('id')}: HTTP {e.code}")
                if added >= PER_RUN:
                    break
            with open(STAMP, "w") as f:
                f.write(datetime.datetime.now().isoformat())
    except (urllib.error.URLError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        print(f"zen-gallery: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    prune()


if __name__ == "__main__":
    main()
