#!/usr/bin/env python3
"""Fill ~/.cache/zen/gallery with public-domain paintings for the zen
"gallery" spacer style, from the Art Institute of Chicago's open API and IIIF
image server: small grayscale PNGs plus a caption each. Stdlib only.

  zen-gallery.py                  add a few random famous paintings (AIC highlights)
  zen-gallery.py --add 27992      add one artwork by AIC id
  zen-gallery.py --add "grande jatte"   ...or the best search hit
  zen-gallery.py --commons "school of athens raphael"   from Wikimedia Commons
                                  (public domain only; needs ImageMagick or sips)
  zen-gallery.py --if-stale 20    (for cron) do nothing if the last run was recent

Only artworks AIC marks is_public_domain are fetched. The spacer reads the
PNGs as data (dimensions are checked) and never runs anything from here.
"""
import argparse
import datetime
import json
import os
import random
import re
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


def prune():
    """Keep the newest KEEP; pinned paintings (a .pin file) are never dropped."""
    metas = sorted(((os.path.getmtime(os.path.join(CACHE, f)), f[:-5]) for f in os.listdir(CACHE)
                    if f.endswith(".json")), reverse=True)
    for _, aid in metas[KEEP:]:
        if not os.path.exists(os.path.join(CACHE, aid + ".pin")):
            for ext in (".png", "-color.png", ".json"):
                try:
                    os.remove(os.path.join(CACHE, aid + ext))
                except OSError:
                    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--add", help="AIC artwork id or search terms")
    ap.add_argument("--commons", help="search Wikimedia Commons (public domain only)")
    ap.add_argument("--pin", action="store_true", help="with --add/--commons: never prune it")
    ap.add_argument("--if-stale", type=float, metavar="HOURS")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    if args.if_stale and os.path.exists(STAMP) and time.time() - os.path.getmtime(STAMP) < args.if_stale * 3600:
        return
    try:
        if args.commons:
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
