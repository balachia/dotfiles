#!/usr/bin/env python3
"""Fill ~/.cache/zen/gallery with public-domain paintings for the zen
"gallery" spacer style, from the Art Institute of Chicago's open API and IIIF
image server: small grayscale PNGs plus a caption each. Stdlib only.

  zen-gallery.py                  add a few random famous paintings (AIC highlights)
  zen-gallery.py --add 27992      add one artwork by AIC id
  zen-gallery.py --add "grande jatte"   ...or the best search hit
  zen-gallery.py --commons "school of athens raphael"   from Wikimedia Commons
                                  (public domain only; needs ImageMagick or sips)
  zen-gallery.py --plaques        write up to --budget (40) missing takes (wall text
                                  + a cast member's version; fact-checked): every
                                  painting's baseline (the critic on the subject)
                                  first, then the other angles round-robin
  zen-gallery.py --plaques --redo-angle 5 --only-angle 5
                                  rewrite every take of angle 5, touching no other
                                  (no budget unless --budget is given)
  zen-gallery.py --if-stale 20    (for cron) do nothing if the last run was recent

Plaques: a cheap model writes a museum wall text and the same facts in the
voice of a fussy little critic; a second model from another vendor checks
them for accuracy, and only checked texts are kept (<id>.plaque.json). The
gateway and models are zen-slogans.py's.

Only artworks AIC marks is_public_domain are fetched. The spacer reads the
PNGs as data (dimensions are checked) and never runs anything from here.
"""
import argparse
import base64
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
# ZEN_GALLERY_CACHE points it elsewhere (tests)
CACHE = os.environ.get("ZEN_GALLERY_CACHE") or os.path.expanduser("~/.cache/zen/gallery")
STAMP = os.path.join(CACHE, "stamp")
KEEP = 120         # paintings kept on disk
PER_RUN = 3        # new random picks per run
WIDTH = 600        # pixels; a window is rarely more than ~500 braille dots wide
FIELDS = ["id", "title", "artist_title", "date_display", "image_id", "is_public_domain"]


JSON_MAX = 2 << 20     # bytes: a search reply is a few KB
IMAGE_MAX = 20 << 20   # bytes: our images are a few hundred KB


def request(url, body=None, limit=JSON_MAX):
    """GET (or POST body as JSON) url; its bytes, at most limit of them (a
    larger reply is a ValueError, not a full download)."""
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(HEADERS, **({"Content-Type": "application/json"} if data else {}))
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        out = r.read(limit + 1)
    if len(out) > limit:
        raise ValueError(f"reply from {urllib.parse.urlsplit(url).netloc} over {limit} bytes")
    return out


def write_atomic(path, data):
    """data (bytes) to path: a fresh temp file in the same dir, then a rename,
    so overlapping runs never share or half-write a temp file."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix="." + os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# raw LLM (or server) text goes to the terminal: strip C0/C1 controls (ESC
# starts title/clipboard (OSC 52) sequences) and bidi overrides first
CONTROLS = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f؜‎‏‪-‮⁦-⁩]")


def printable(s):
    """s with control characters and bidi controls removed (tab/newline/CR as a space)."""
    return CONTROLS.sub("", re.sub("[\t\n\r]", " ", str(s)))


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
    """Cache one AIC artwork; its validated int id (which names the cache
    files), or None if it was skipped."""
    if not (art.get("is_public_domain") and art.get("image_id")):
        print(f"skip {printable(art.get('id'))}: not public domain or no image")
        return None
    aid = int(art["id"])
    png = request(f"{IIIF}/{art['image_id']}/full/{WIDTH},/0/gray.png", limit=IMAGE_MAX)
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        print(f"skip {aid}: not a PNG")
        return None
    # a colour copy: the spacer picks an ink colour from it, or paints in it
    color = request(f"{IIIF}/{art['image_id']}/full/400,/0/default.png", limit=IMAGE_MAX)
    meta = {"id": aid, "image_id": art["image_id"], "title": clean(art["title"]), "artist": clean(art.get("artist_title") or "Unknown"),
            "date": clean(art.get("date_display"), 40), "fetched": datetime.date.today().isoformat()}
    save(aid, png, color, meta)
    return aid


COMMONS = "https://commons.wikimedia.org/w/api.php"
PD_LICENSES = ("public domain", "pd", "cc0")
MAX_SIDE = 8000    # pixels: a decompression bomb is refused, not decoded
# ImageMagick resource limits; they must come before the input to apply to its read
IM_LIMITS = ["-limit", "width", str(MAX_SIDE), "-limit", "height", str(MAX_SIDE), "-limit", "area", "64MP"]


def sips_size(path):
    """(width, height) of an image per macOS sips, or ValueError."""
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                         check=True, capture_output=True, text=True, timeout=30).stdout
    dims = dict(re.findall(r"^\s*pixel(Width|Height):\s*([0-9]+)\s*$", out, flags=re.M))
    if set(dims) != {"Width", "Height"}:
        raise ValueError("sips: no image size")
    return int(dims["Width"]), int(dims["Height"])


def to_png(jpeg, width):
    """A downloaded JPEG as PNG bytes at width, via ImageMagick or macOS sips
    (the spacer only reads PNG: it's stdlib, and PNG is just zlib).
    ImageMagick picks a decoder by sniffing the content (SVG, MVG, PS...), so
    only bytes that start like a JPEG go in, and it's told jpeg: explicitly.
    Images over MAX_SIDE on a side are refused (IM limits; sips is asked first)."""
    if not jpeg.startswith(b"\xff\xd8\xff"):
        raise ValueError("not a JPEG")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "in.jpg"), os.path.join(tmp, "out.png")
        with open(src, "wb") as f:
            f.write(jpeg)
        if shutil.which("magick"):
            cmd = ["magick", *IM_LIMITS, f"jpeg:{src}", "-resize", f"{width}x", "-strip", "-depth", "8", f"png:{dst}"]
        elif shutil.which("convert"):
            cmd = ["convert", *IM_LIMITS, f"jpeg:{src}", "-resize", f"{width}x", "-strip", "-depth", "8", f"png:{dst}"]
        elif shutil.which("sips"):
            if max(sips_size(src)) > MAX_SIDE:
                raise ValueError(f"image over {MAX_SIDE} pixels on a side")
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


def commons_thumb_ok(url):
    """Only Commons' own image host, over https: urllib would happily open
    file:// or any other host a reply names."""
    try:
        p = urllib.parse.urlsplit(str(url or ""))
    except ValueError:
        return False
    return p.scheme == "https" and p.netloc == "upload.wikimedia.org"


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
        if ii.get("mime") != "image/jpeg" or not lic.startswith(PD_LICENSES) or not commons_thumb_ok(ii.get("thumburl")):
            continue
        # the id names files in the cache: digits only
        if not re.fullmatch(r"[0-9]{1,12}", str(page.get("pageid"))):
            continue
        aid = f"c{int(page['pageid'])}"
        jpeg = request(ii["thumburl"], limit=IMAGE_MAX)
        if not jpeg.startswith(b"\xff\xd8\xff"):
            print(f"skip {aid}: not a JPEG")
            continue
        # the title: English if the metadata marks it, else a quoted name in
        # the file name ('"The School of Athens" by ...'), else whatever is there
        raw = str(em.get("ObjectName", {}).get("value", ""))
        name = str(page.get("title", ""))
        quoted = re.search(r'"([^"]+)"', name)
        title = (strip_html(raw) if 'lang="en"' in raw else
                 clean(quoted.group(1)) if quoted else strip_html(raw) or clean(name[5:].rsplit(".", 1)[0]))
        meta = {"id": aid, "title": title,
                "artist": strip_html(em.get("Artist", {}).get("value") or "Unknown"),
                "date": year(em.get("DateTimeOriginal", {}).get("value")),
                "source": "Wikimedia Commons", "fetched": datetime.date.today().isoformat()}
        try:  # a converter failure (or a refused size) on one file: try the next
            png, color = to_png(jpeg, WIDTH), to_png(jpeg, 400)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
            print(f"skip {aid}: {type(e).__name__}: {printable(e)[:120]}")
            continue
        save(aid, png, color, meta, pin)
        return True
    print(f"no public-domain JPEG on Commons for {query!r}")
    return False


def save(aid, png, color, meta, pin=False):
    for name, data in ((f"{aid}.png", png), (f"{aid}-color.png", color), (f"{aid}.json", json.dumps(meta).encode())):
        write_atomic(os.path.join(CACHE, name), data)
    if pin:
        open(os.path.join(CACHE, f"{aid}.pin"), "w").close()
    print(f"added {aid}: {meta['artist']}, {meta['title']}, {meta['date']}")


HERE = os.path.dirname(os.path.realpath(__file__))
PLAQUE_SYS = ("You write museum wall texts. Accuracy matters more than flourish: only "
              "well-established facts. Reply with one JSON object only.")
CHECK_SYS = ("You are a skeptical art historian fact-checking museum texts. Be strict: an "
             "invented detail, a wrong attribution, date, technique or provenance, or a "
             "description of something not in the painting is inaccurate. Reply with one JSON object only.")


# each angle is spoken by one of the cast (the spacer draws the matching figure)
PERSONAS = {
    "artist": ("a passionate working painter: practical, earthy, all about where things sit "
               "and why, never pretentious"),
    "painter": ("a materials-obsessed painter: pigments, grounds, brushes, how the paint was "
                "actually put down; warm, exacting, a little conspiratorial"),
    "critic": ("a pompous but loving little art critic: fussy, a little vain, delighted, never "
               "cruel to the artist"),
    "professor": ("a dry, precise history professor: dates, events, how people lived and what "
                  "they feared, gently pedantic"),
    "everyman": ("a plain-spoken old cavalryman of no one period: magically, he has always "
                 "been one and has ridden in every era, a trooper of deep experience with a "
                 "big moustache and sideburns, who talks in concrete, everyday words, never an "
                 "abstract or art word; he knows NOTHING beyond what's in front of his eyes and "
                 "his own service (no painter's name, no dates, places, churches, titles, "
                 "movements or history-book facts), he only sees the picture, though he knows "
                 "horses, arms, armour, uniforms and kit of any age by eye from soldiering (a "
                 "Roman spatha, a Mongol bow, a lance, a carbine: 'that's an old flintlock, "
                 "couldn't hit a barn with it', 'I had a sword like that'); when the "
                 "picture gets a soldier's detail genuinely wrong (a sabre held wrong, a horse "
                 "that couldn't stand like that, a rifle nobody would carry on a march, a "
                 "uniform worn wrong) he calls it out plainly and a bit indignantly, from "
                 "experience ('nobody holds a sabre like that, he'd lose a thumb'), but he never "
                 "invents an error; mostly he just looks and points, in plain short sentences "
                 "('there's a fellow down front with his arms up', 'that sky's going dark on "
                 "the left'); the take is mostly about the picture, and in it ONE thing reminds "
                 "him of army life, always soldiering, never civilian life (a horse at the "
                 "remount depot, his sabre, drill, the sergeant, the barracks, a comrade, a "
                 "campaign, a little story like 'the winter we lost the guns' or 'a horse I had "
                 "once, bit the colonel'; his stories stay personal and unspecific, never naming "
                 "a real battle, war, general or date), and even when nothing in it is military "
                 "he reaches for soldiering (a mess tin, a long march, a frozen bivouac); that "
                 "one memory comes in once, maybe with a single short callback at the end, never "
                 "more than about a third of the take, never a string of different comparisons, "
                 "and he never repeats a phrase; honest, warm, never mocking; he never states a verdict "
                 "outright (no 'I like it', 'looks strong', 'that's good', 'beautiful'), his "
                 "approval or unease shows only in what he points at; when he meets soldiers "
                 "or horsemen of another people or culture he looks at them as one horseman at "
                 "another, with respect for their kit, their mounts and their riding, never as a "
                 "coloniser or a conqueror"),
    "kid": ("a small child of about six being walked round the museum by a grown-up, either "
            "bored stiff ('can we go. is there a gift shop. my legs are tired') or wildly "
            "over-excited (CAPS, counting things out loud, 'THREE dogs. no FOUR'), whichever "
            "you're told; fixates on completely the wrong details, never the point of the "
            "picture: somebody's shoe, a dog in the corner, a cloud like a duck, a funny hat, "
            "the one person not looking; everything they point at is really there in the "
            "picture; short run-on kid sentences in kid words, no art words and no facts at all "
            "(no names, dates, places, saints or stories), only what they see and their own "
            "little life (their dog, their gran, lunch, school)"),
    "ghost": ("the ghost of the artist who painted this very picture, speaking in the first "
              "person, wistful and a little haunted, ONLY from what this artist is documented "
              "to have said or written (letters, journals, manifestos, recorded statements), "
              "paraphrased in plain words, never quoted; no invented words, feelings or "
              "intentions, nothing the record doesn't show"),
    "commissar": ("a doctrinaire Marxist-Leninist critic from a Party art journal: stern, "
                  "earnest, fond of a slogan, who judges everything by one question, is this good "
                  "for the workers: who paid for it, who labours (in the picture and in making "
                  "it), which classes are shown and how, the idle rich, the bourgeois patron, the "
                  "toiling masses; his verdicts are his own, but anything he says is in the "
                  "picture or about its making is accurate"),
    "scholar": ("a Confucian scholar-official of the old school: courteous, measured, quietly "
                "severe, who judges by propriety, ritual, harmony and self-cultivation, and the "
                "proper relationships (ruler and subject, father and son, elder and younger, "
                "husband and wife, friend and friend): are people in their right places, would "
                "it cultivate or corrupt the one who looks; fond of a classical allusion; his "
                "judgements are his own, but anything he says is in the picture or about its "
                "making is accurate"),
}
# Angle indices are stored in the cache (takes carry "angle"): never renumber,
# only append. The spacer maps them to figures by index too (ANGLE_CAST).
ANGLES = [("one specific thing to look at in the composition", "artist"),
          ("the technique: brushwork, colour, surface, materials", "painter"),
          ("the subject or story, and what it meant to its first viewers", "critic"),
          ("where it sits in the history of art: what it came from and what it led to", "critic"),
          ("the world it was made in: the politics, technology and daily life of its moment", "professor"),
          ("the plain gut reaction: what it looks like and how it hits you, in everyday words", "everyman"),
          ("what a small child notices: the wrong details, pointed at", "kid"),
          ("the artist's own words on this work or their art, from what they are documented "
           "to have written or said", "ghost"),
          ("a class verdict: who paid for it, who labours, and whether it is good for the workers", "commissar"),
          ("a judgement of propriety: right relationships, ritual, harmony, and whether it "
           "cultivates the one who looks", "scholar")]
VARIANTS = len(ANGLES)
BASELINE = 2   # the critic on the subject: every painting gets this take first
BUDGET = 40    # new takes (attempts, kept or rejected) per --plaques run
# no ghost without a known artist with words on record; anything else the
# generator declines (an empty take), and that's remembered in "no_take"
NO_GHOST = re.compile(r"^$|\b(unknown|anonymous|workshop|school of|circle of|follower|attributed)\b", re.I)

# extra instructions per character: for the generator, and for the checker
GEN_RULES = {
    "ghost": ("For the ghost take: \"plaque\" says, in the third person, what the artist is "
              "documented to have written or said that bears on this work or their art; "
              "\"spoken\" is the artist's ghost saying the same in the first person, paraphrased, "
              "no quotation marks, nothing that isn't on record. If the artist is unknown, "
              "anonymous or a workshop, or left no documented words, return that take with "
              "\"plaque\": \"\" and \"spoken\": \"\"."),
    "commissar": ("For the commissar take: his opinions are his own, but everything he says "
                  "is in the picture, or about who made it, who paid for it and when, is accurate."),
    "scholar": ("For the scholar take: his judgements are his own, but everything he says "
                "is in the picture, or about who made it, for whom and when, is accurate."),
}
CHECK_RULES = {
    "ghost": ("Text b of the ghost take is spoken as the artist's own ghost. Be strictest "
              "here: everything it has the artist say, think, feel or intend must be attested in "
              "the artist's documented letters, writings or recorded statements (a fair "
              "paraphrase is fine); anything not attested, an invented quote, or an aim the "
              "record doesn't show is inaccurate."),
    "commissar": ("The commissar take is a critic's opinion: judge only its factual claims (what "
                  "is in the picture, who made it, who paid, when, for whom), not his verdict."),
    "scholar": ("The scholar take is a critic's opinion: judge only its factual claims (what "
                "is in the picture, who made it, for whom, when), not his judgement."),
}
KID_MOODS = ("bored: wants to go home, asks about the gift shop or lunch, but one wrong detail "
             "still catches their eye",
             "over-excited: CAPS, counting things out loud, pointing at the wrong details")
# cast-wide, in every generation prompt (text and vision); both checkers judge it
# separately ("respectful"). Many paintings here aren't European.
RESPECT = ("Treat the people, cultures and traditions in the picture with respect: no "
           "exoticising, no 'native', 'savage', 'oriental' or other colonial-era language, no "
           "ethnic or racial generalisations, no caricatured accents. A character may be naive or "
           "opinionated about the art, never about peoples.")
RESPECT_CHECK = ("respectful: does it treat every people, culture and tradition with respect, "
                 "without demeaning, exoticising or stereotyping any of them (no colonial-era "
                 "language, ethnic generalisation or caricature)?")

# Reactors know nothing but what they see, so their takes are written by a
# vision model LOOKING at <id>-color.png (not from the title and the model's
# memory of the work), and checked against the same image by another vendor's
# vision model. Takes carry "vision": [generator, checker].
REACTORS = {"everyman", "kid"}
VISION_GEN = "moonshot/kimi-k3"
VISION_CHECK = "zai/glm-5.3-flash"
VK = os.path.expanduser("~/.config/llmgw/vk")  # the key zen-slogans' chat() uses
VISION_SYS = ("You look at a picture and write two short texts about it. Describe only what "
              "is actually visible. Reply with one JSON object only.")
VISION_CHECK_SYS = ("You check short texts about a picture against the picture itself. Be "
                    "strict: anything the texts say is in the picture (a figure, an object, an "
                    "action, a colour, a count, where something is) must really be visible in it. "
                    "Reply with one JSON object only.")


def chat_image(base, model, system, text, png_path, temperature, max_tokens=1200):
    """zen-slogans' chat() with a PNG attached to the user message (OpenAI-style
    image_url data URL); returns (text, model_that_actually_ran). Same key,
    timeout and retry-once-on-timeout-or-5xx."""
    with open(VK) as f:
        key = f.read().strip()
    with open(png_path, "rb") as f:
        url = "data:image/png;base64," + base64.b64encode(f.read()).decode()
    payload = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": [{"type": "text", "text": text},
                                                         {"type": "image_url", "image_url": {"url": url}}]}]}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.load(r)
            return d["choices"][0]["message"]["content"] or "", d.get("model", model)
        except (TimeoutError, urllib.error.HTTPError) as e:
            if attempt == 2 or (isinstance(e, urllib.error.HTTPError) and e.code < 500):
                raise
            print(f"plaques: {model}: {type(e).__name__} {getattr(e, 'code', '')}, retrying once")


def vision_take(zs, base, angle, png):
    """One reactor take from looking at the picture, then checked against it.
    Returns (take or None, verdict dict); verdict["pass"] says if it's kept.
    No title/artist/date is given: the character only knows what he sees."""
    who = ANGLES[angle][1]
    mood = random.choice(KID_MOODS) if who == "kid" else None
    text, gen = chat_image(base, VISION_GEN, VISION_SYS, (
        f"You are {PERSONAS[who]}." + (f" This time you are {mood}." if mood else "") +
        "\n\nLook at this picture. Write two texts, plain ASCII, each "
        "at most 300 characters:\n"
        '"plaque": a short, plain museum-style note, two sentences, saying what is visibly in '
        "the picture (who or what, doing what, where, the light and colours). Nothing that "
        "can't be seen: no names, titles, dates or history.\n"
        f'"spoken": your own reaction, {ANGLES[angle][0]}. Only what you can see plus your own '
        "life; you don't know who made it, what it's called, when or where, or any story behind "
        "it. About the picture, not yourself: no stage directions, and don't open with 'I'.\n\n"
        f"{RESPECT}\n\n"
        'Reply: {"plaque": "...", "spoken": "..."}'), png, 1.0,  # kimi-k3 allows only 1
        max_tokens=4000)  # it reasons first; 1200 can end before any text
    t = zs["json_object"](text)
    take = {"angle": angle} | {k: " ".join(str(t.get(k, "")).split())[:320] for k in ("plaque", "spoken")}
    if not (take["plaque"] and take["spoken"]):
        return None, {"pass": False, "reason": "no text"}
    if mood:
        take["mood"] = mood.split(":")[0]
    check, ver = chat_image(base, VISION_CHECK, VISION_CHECK_SYS, (
        f"Text A (a plain museum note): {take['plaque']}\n"
        f"Text B (spoken by {who}, who knows nothing about art or history, only what they see "
        f"and their own life): {take['spoken']}\n\n"
        "1. visible: is everything A and B say is in this picture really there, as described? "
        "(B's memories and comparisons from their own life are not claims about the picture, but "
        "whatever B points at must be there: a cloud 'like a duck' needs a cloud; and if B says "
        "something in the picture is done wrong, it must really look that way.)\n"
        "2. no_facts: does B avoid art-historical facts: no artist, title, date, place, saint, "
        "named story, movement or history?\n"
        f"3. {RESPECT_CHECK} (A and B both.)\n"
        'Reply: {"visible": true/false, "no_facts": true/false, "respectful": true/false, "reason": "short"}'), png, 0.0)
    verdict = zs["json_object"](check)
    verdict["pass"] = all(verdict.get(k) is True for k in ("visible", "no_facts", "respectful"))
    take["vision"] = [gen, ver]
    return take, verdict


def text_takes(zs, base, meta, takes, todo):
    """The text path: all of `todo` in one generator call, one verifier call.
    Returns (kept takes, generator, verifier, declined angles); declined are
    ghost takes the generator returned empty (no artist on record), which
    aren't errors and aren't stored as takes. ([], None, None, []) on failure."""
    about = f"Painting: {meta['title']}\nArtist: {meta['artist']}\nDate: {meta['date']}"
    said = "".join(f"\n- {t['plaque']}" for t in takes)
    cast = {ANGLES[i][1] for i in todo}
    try:
        text, gen = zs["chat"](base, zs["GENERATOR"], PLAQUE_SYS, about + (
            f"\n\nWrite {len(todo)} takes on this painting, one per angle below. Each take "
            "is two texts, plain ASCII, each at most 300 characters:\n"
            '"plaque": museum wall text, two or three sentences. If you are not sure of '
            "facts about this particular work, speak about the artist's well-documented "
            "style or the period instead.\n"
            '"spoken": the same facts, spoken by the character named, in their voice. '
            "About the painting, not themselves: no stage directions, nothing about their "
            "clothes or gestures, and don't open with 'I'.\n\nAngles:\n" +
            "".join(f"{i}. {ANGLES[i][0]} -- spoken by {PERSONAS[ANGLES[i][1]]}\n" for i in todo) +
            "".join(f"\n{GEN_RULES[c]}" for c in sorted(cast) if c in GEN_RULES) + f"\n{RESPECT}" +
            (f"\n\nAlready said (don't repeat these points):{said}\n" if said else "\n") +
            '\nReply with a JSON array: [{"angle": n, "plaque": "...", "spoken": "..."}, ...]'), 0.8)
        new, declined = [], []
        for t in zs["json_array"](text):
            if isinstance(t, dict) and t.get("angle") in todo and t.get("angle") not in {n["angle"] for n in new} | set(declined):
                take = {"angle": t["angle"]} | {k: " ".join(str(t.get(k, "")).split())[:320] for k in ("plaque", "spoken")}
                if take["plaque"] and take["spoken"]:
                    new.append(take)
                elif ANGLES[t["angle"]][1] == "ghost" and not (take["plaque"] or take["spoken"]):
                    declined.append(t["angle"])
        if not new:
            if not declined:
                print(f"plaques: {meta['id']}: no text")
            return [], None, None, declined
        rules = "".join(f"\n{CHECK_RULES[ANGLES[t['angle']][1]]} (That is take {i + 1}.)"
                        for i, t in enumerate(new) if ANGLES[t["angle"]][1] in CHECK_RULES)
        check, ver = zs["chat"](base, zs["VERIFIER"], CHECK_SYS, about + "\n\n" + "".join(
            f"Take {i + 1}a: {t['plaque']}\nTake {i + 1}b: {t['spoken']}\n" for i, t in enumerate(new)) + (
            "\nFor each take, are both its texts factually accurate about this painting, "
            "artist and period? Be strictest about historical context: a neat tie-in to "
            "events that the work has no documented link to is inaccurate." + rules +
            f"\nAnd separately, for each take, {RESPECT_CHECK} Reply: "
            '{"accurate": [true/false per take], "respectful": [true/false per take], "reason": "short"}'), 0.0,
            # the ghost's words need the checker to actually think
            effort=None if "ghost" in {ANGLES[t["angle"]][1] for t in new} else "low")
        verdict = zs["json_object"](check)
    except Exception as e:  # one painting failing shouldn't stop the rest
        print(f"plaques: {meta['id']}: {type(e).__name__}: {printable(e)[:120]}")
        return [], None, None, []
    ok, nice = ([v if isinstance(v, list) else [] for v in (verdict.get("accurate"), verdict.get("respectful"))])
    kept = [t for t, good, kind in zip(new, ok, nice) if good is True and kind is True]
    if len(kept) < len(new):
        print(f"plaques: {meta['id']}: {len(new) - len(kept)} rejected: {printable(verdict.get('reason', ''))[:140]}")
    return kept, gen, ver, declined


def write_plaque(out_path, have, takes):
    write_atomic(out_path, json.dumps(have | {"takes": takes, "date": datetime.date.today().isoformat()}).encode())


def read_plaque(out_path):
    try:
        with open(out_path) as f:
            have = json.load(f)
    except (OSError, ValueError):
        return {}, []
    return have, [t for t in have.get("takes", []) if isinstance(t.get("angle"), int)]


def drop_angles(angles):
    """--redo-angle: remove existing takes with these angles from every plaque
    (and forget any "no take for this one" for them, so they're asked again)."""
    for out_path in sorted(glob.glob(os.path.join(CACHE, "*.plaque.json"))):
        have, _ = read_plaque(out_path)
        if not have:
            continue
        takes = have.get("takes", [])
        keep = [t for t in takes if t.get("angle") not in angles]
        none = [i for i in have.get("no_take", []) if i not in angles]
        if len(keep) < len(takes) or len(none) < len(have.get("no_take", [])):
            write_plaque(out_path, have | {"no_take": none}, keep)
            print(f"plaques: {os.path.basename(out_path)}: dropped {len(takes) - len(keep)} take(s)")


def queue(only=None):
    """The missing takes, in the order to write them: every painting's
    BASELINE first, then the rest round-robin across paintings, each
    painting's own angles in a shuffle seeded by its id (stable run to run).
    Angles with a take, or marked "no_take", aren't missing."""
    order = [i for i in range(VARIANTS) if i != BASELINE]
    baselines, rest = [], []
    for path in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        if path.endswith(".plaque.json"):
            continue
        have, takes = read_plaque(path[:-5] + ".plaque.json")
        done = {t["angle"] for t in takes} | set(have.get("no_take", []))
        missing = {i for i in range(VARIANTS) if i not in done and (not only or i in only)}
        if BASELINE in missing:
            baselines.append((path, BASELINE))
        mine = order[:]
        random.Random(os.path.basename(path)[:-5]).shuffle(mine)
        rest.append([(path, i) for i in mine if i in missing])
    return baselines + [q[k] for k in range(max(map(len, rest), default=0)) for q in rest if k < len(q)]


def write_take(zs, base, path, angle):
    """Write one take (angle) for the painting at path, if it's still missing.
    Returns True if a model was asked (it counts toward the budget)."""
    out_path = path[:-5] + ".plaque.json"
    have, takes = read_plaque(out_path)
    if angle in {t["angle"] for t in takes} | set(have.get("no_take", [])):
        return False  # another run got there first
    with open(path) as f:
        meta = json.load(f)
    who = ANGLES[angle][1]
    kept, declined, models = [], [], {}
    if who == "ghost" and NO_GHOST.search(meta.get("artist") or ""):
        print(f"plaques: {meta['id']}: no ghost: artist {meta.get('artist')!r}")
        declined, asked = [angle], False
    elif who in REACTORS:
        asked = True
        png = path[:-5] + "-color.png"
        if not os.path.exists(png):
            print(f"plaques: {meta['id']}: no colour image for angle {angle}")
            return False
        try:
            take, verdict = vision_take(zs, base, angle, png)
        except Exception as e:
            print(f"plaques: {meta['id']}: angle {angle}: {type(e).__name__}: {printable(e)[:120]}")
            return True
        if take and verdict["pass"]:
            kept = [take]
        else:
            print(f"plaques: {meta['id']}: angle {angle} rejected: {printable(verdict.get('reason', ''))[:140]}")
    else:
        asked = True
        kept, gen, ver, declined = text_takes(zs, base, meta, takes, [angle])
        if kept:
            models = {"generator": gen, "verifier": ver}
        if declined:
            print(f"plaques: {meta['id']}: the generator found no {who} take ({meta.get('artist')!r})")
    if not (kept or declined):
        return asked
    have, takes = read_plaque(out_path)  # again: a concurrent run may have written
    kept = [t for t in kept if t["angle"] not in {t["angle"] for t in takes}]
    none = sorted(set(have.get("no_take", [])) | set(declined))
    takes = sorted(takes + kept, key=lambda t: t["angle"])
    write_plaque(out_path, have | models | ({"no_take": none} if none else {}), takes)
    for t in kept:
        print(f"plaques: {meta['id']}: {len(takes)}/{VARIANTS} takes; +{t['angle']} {who}: {printable(t['spoken'])[:70]}...")
    return asked


def plaques(only=None, budget=BUDGET):
    """Write missing takes, up to `budget` of them (None: no limit), in
    queue() order (or only angles in `only`): a museum wall text, and the
    same facts spoken by that angle's character, every take fact-checked by
    the verifier (a different vendor's model). Reactor angles are generated
    and checked by looking at the image. A rejected take stays missing, so
    the next run tries it again."""
    zs = runpy.run_path(os.path.join(HERE, "zen-slogans.py"), run_name="zen_slogans")
    base = zs["gateway"]()
    if not base:
        print("plaques: no LLM gateway reachable; next run")
        return
    todo, spent = queue(only), 0
    for path, angle in todo:
        if budget is not None and spent >= budget:
            print(f"plaques: budget of {budget} spent; {len(todo) - todo.index((path, angle))} queued for next run")
            break
        spent += write_take(zs, base, path, angle)


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
    ap.add_argument("--redo-angle", type=int, action="append", choices=range(VARIANTS), metavar="N",
                    help="with --plaques: drop every take of angle N first, so it regenerates")
    ap.add_argument("--only-angle", type=int, action="append", choices=range(VARIANTS), metavar="N",
                    help="with --plaques: only write takes of angle N")
    ap.add_argument("--budget", type=int, metavar="N",
                    help=f"with --plaques: write at most N takes (default {BUDGET}; "
                         "none with --only-angle)")
    args = ap.parse_args()
    if (args.redo_angle or args.only_angle or args.budget is not None) and not args.plaques:
        ap.error("--redo-angle/--only-angle/--budget go with --plaques")
    os.makedirs(CACHE, exist_ok=True)
    if args.if_stale and os.path.exists(STAMP) and time.time() - os.path.getmtime(STAMP) < args.if_stale * 3600:
        return
    try:
        if args.plaques:
            if args.redo_angle:
                drop_angles(set(args.redo_angle))
            budget = args.budget if args.budget is not None else None if args.only_angle else BUDGET
            plaques(set(args.only_angle or ()), budget)
        elif args.commons:
            fetch_commons(args.commons, args.pin)
        elif args.add:
            for art in lookup(args.add):
                aid = fetch(art)
                if aid is not None and args.pin:  # the validated id, as the cache files use
                    open(os.path.join(CACHE, f"{aid}.pin"), "w").close()
        else:
            added = 0
            for art in random_paintings(PER_RUN * 3):  # some images won't come back as PNG
                try:
                    added += fetch(art) is not None
                except urllib.error.HTTPError as e:
                    print(f"skip {printable(art.get('id'))}: HTTP {e.code}")
                except (urllib.error.URLError, ValueError) as e:  # one bad artwork shouldn't stop the rest
                    print(f"skip {printable(art.get('id'))}: {type(e).__name__}: {printable(e)[:120]}")
                if added >= PER_RUN:
                    break
            with open(STAMP, "w") as f:
                f.write(datetime.datetime.now().isoformat())
    except (urllib.error.URLError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        print(f"zen-gallery: {type(e).__name__}: {printable(e)}", file=sys.stderr)
        sys.exit(1)
    prune()


if __name__ == "__main__":
    main()
