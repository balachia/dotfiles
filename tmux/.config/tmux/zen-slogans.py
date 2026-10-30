#!/usr/bin/env python3
# stdlib only, on purpose: runs on whatever system python3 is around.
"""zen-slogans: grow the garden yard sign's slogan buckets with an LLM.

Meant for cron (hourly with --if-stale 20, so a sleeping laptop catches up).
Per bucket it:
  1. generates candidates with a cheap model, from a precise pattern spec,
     each with its basis (concept/finding + citation);
  2. has a *different* model fact-check them as a skeptic (true and settled?
     real citation? fits the pattern?) -- two vendors are less likely to
     hallucinate the same thing;
  3. filters in code (pattern, length, plain printable text, no duplicates);
  4. keeps survivors in ~/.cache/zen/slogans.json, which zen-spacer.py merges
     into its built-in buckets. Rejects (with reasons) go to slogans.log.

LLM output is only ever data: sanitized here and again when zen-spacer reads
it. The gateway is the homelab Bifrost (llmgw); the virtual key is read from
~/.config/llmgw/vk at call time and never logged.

Usage: zen-slogans.py [--if-stale HOURS] [--dry-run] [--bucket NAME ...]
"""
import argparse
import datetime
import json
import os
import re
import runpy
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
CACHE = os.path.expanduser("~/.cache/zen")
STORE = os.path.join(CACHE, "slogans.json")
LOG = os.path.join(CACHE, "slogans.log")
STAMP = os.path.join(CACHE, "slogans.stamp")
VK = os.path.expanduser("~/.config/llmgw/vk")
# Only this host's own gateway. No fallback to another host's (appa's
# 10.7.15.20 was one): the key would go to it in cleartext, and on a foreign
# network (a laptop away from home) to whatever answers at that address; and
# a key is only valid on the gateway that issued it anyway. No local gateway:
# skip this run.
GATEWAYS = ["http://127.0.0.1:4010"]
GENERATOR = "deepseek/deepseek-flash"
VERIFIER = "zai/glm-5.3"
PER_BUCKET = 6      # candidates asked for per run
KEEP = 40           # newest kept per bucket
MAX_LEN = 48
SAFE = re.compile(r"^[A-Za-z0-9 ,.'%<>=+\-:;!?/()&]+$")  # plain printable text only

# What each bucket is, precisely. Buckets not listed here stay hand-curated.
SPECS = {
    "distinctions": {
        "pattern": "Exactly 'X is not Y' (lowercase, optional leading 'a'/'an'), where X and Y are "
                   "real technical terms from ONE named field (sociology, network science, "
                   "organization theory, statistics, psychometrics, philosophy of science, "
                   "gender studies...) that laypeople treat as synonyms but the field "
                   "carefully distinguishes.",
        "regex": r"^(an? )?[a-z][a-z' -]* is not (an? )?[a-z][a-z' -]*$",
        "check": "Are X and Y both real terms of art in the named field, and does that field "
                 "really distinguish them in the way the basis says?",
    },
    "counterintuitive": {
        "pattern": "A short, plain-language statement of a well-replicated scientific or "
                   "mathematical finding that sounds false to most people (like the friendship "
                   "paradox, Braess's paradox, the birthday problem). Must be TRUE as worded. "
                   "Never contested or popular-myth material (no Mpemba effect, no '10% of the "
                   "brain', no learning styles, no ego depletion, no power posing).",
        "regex": None,
        "check": "Is the statement, exactly as worded, true and scientifically settled? Reject "
                 "anything contested, failed to replicate, a popular myth, or true only with "
                 "caveats the wording drops.",
    },
    "orgs": {
        "pattern": "A terse slogan, at most 8 words, compressing a specific concept from "
                   "organization theory or organizational sociology (institutional theory, "
                   "Weber, March and Simon, Weick, population ecology, decoupling...).",
        "regex": None,
        "check": "Does the slogan faithfully compress the named concept, and is the citation a "
                 "real work by the named author(s)?",
    },
    "networks": {
        "pattern": "A terse slogan, at most 8 words, compressing a specific finding or concept "
                   "from social network analysis or network science (Granovetter, Burt, "
                   "Coleman, Centola, Watts, Christakis and Fowler...).",
        "regex": None,
        "check": "Does the slogan faithfully state the finding or concept, without overclaiming "
                 "(e.g. weak ties help with simple information, not everything)? Is the citation "
                 "real?",
    },
    "metascience": {
        "pattern": "A terse slogan, at most 8 words, for good research practice or a "
                   "science-of-science finding (replication, preregistration, effect sizes, "
                   "open data, citation dynamics, peer review...).",
        "regex": None,
        "check": "Is it sound research-practice advice or an accurate science-of-science claim? "
                 "Is the citation, if any, real?",
    },
}


# raw LLM text (basis, the verifier's reason, error bodies) reaches the log
# and the terminal: strip C0/C1 controls (ESC starts title/clipboard (OSC 52)
# sequences) and bidi overrides first
CONTROLS = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def printable(s):
    """s with control characters and bidi controls removed (tab/newline/CR as a space)."""
    return CONTROLS.sub("", re.sub("[\t\n\r]", " ", str(s)))


def write_atomic(path, text):
    """text to path: a fresh temp file in the same dir, then a rename, so
    overlapping runs never share or half-write a temp file."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix="." + os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def log(msg):
    os.makedirs(CACHE, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {printable(msg)}\n")


def gateway():
    for base in GATEWAYS:
        try:
            with urllib.request.urlopen(base + "/health", timeout=5) as r:
                if r.status == 200:
                    return base
        except OSError:
            continue
    return None


def chat(base, model, system, user, temperature, effort=None):
    """One chat completion; returns (text, model_that_actually_ran). Retries
    once on a timeout or gateway 5xx: a long-thinking model can outlast the
    gateway's own upstream timeout."""
    with open(VK) as f:
        key = f.read().strip()
    payload = {"model": model, "temperature": temperature,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]}
    if effort:
        payload["reasoning_effort"] = effort  # passes through Bifrost as-is
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:  # fine for a background job
                d = json.load(r)
            return d["choices"][0]["message"]["content"] or "", d.get("model", model)
        except (TimeoutError, urllib.error.HTTPError) as e:
            if attempt == 2 or (isinstance(e, urllib.error.HTTPError) and e.code < 500):
                raise
            log(f"{model}: {type(e).__name__} {getattr(e, 'code', '')}, retrying once")


def json_array(text):
    """The first JSON array in a model reply (tolerates code fences and chatter)."""
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        v = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return [x for x in v if isinstance(x, dict)]


def json_object(text):
    """The first JSON object in a model reply."""
    start, end = text.find("{"), text.rfind("}")
    try:
        v = json.loads(text[start:end + 1]) if 0 <= start < end else {}
    except json.JSONDecodeError:
        return {}
    return v if isinstance(v, dict) else {}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def clean(s):
    s = " ".join(str(s).split()).rstrip(".")
    return s if s and len(s) <= MAX_LEN and SAFE.match(s) else None


def decap(s, basis=""):
    """The sign's voice is lowercase. Undo a sentence-case capital on the first
    word, unless it's an acronym (R&D, DNA) or a name: cited as one in the
    basis ("Weick 1995", "Burt and Coleman") or capitalized mid-sentence there."""
    first = s.split(" ", 1)[0]
    if not (first[:1].isupper() and first[1:].islower()):
        return s
    w = re.escape(re.sub(r"'s$", "", first))
    if re.search(rf"\b{w}(,? (\(?\d{{4}}|and |& |et al)|'s\b)", basis) or re.search(rf"[a-z,;(] {w}\b", basis):
        return s
    return first.lower() + s[len(first):]


VER_SYS = ("You are a skeptical fact-checker and domain expert reviewing slogans for a sign. "
           "Be strict: a finding with a well-known critique, a failed or mixed replication, or "
           "real controversy in its field counts as contested, however famous it is. "
           "Reply with one JSON object only.")


def verify(base, spec, c):
    """Check one candidate with a checklist; the code, not the model's own
    verdict, decides: true as worded, not contested, citation real, fits the
    pattern. Returns (ok, reason, verifier_model)."""
    user = (f"Bucket rule: {spec['pattern']}\nAlso check: {spec['check']}\n\n"
            f"Candidate: {c['slogan']}\nWriter's claimed basis: {c['basis']}\n\n"
            'Reply: {"true_as_worded": bool, "contested": bool, "citation_real": bool, '
            '"fits_pattern": bool, "reason": short}')
    try:
        text, model = chat(base, VERIFIER, VER_SYS, user, 0.0)
    except (TimeoutError, urllib.error.HTTPError):  # thinking outlasted the gateway
        text, model = chat(base, VERIFIER, VER_SYS, user, 0.0, effort="low")
    v = json_object(text)
    ok = (v.get("true_as_worded") is True and v.get("contested") is False
          and v.get("citation_real") is True and v.get("fits_pattern") is True)
    flags = ",".join(k for k, bad in (("false", v.get("true_as_worded") is not True),
                                      ("contested", v.get("contested") is not False),
                                      ("citation", v.get("citation_real") is not True),
                                      ("pattern", v.get("fits_pattern") is not True)) if bad)
    reason = " ".join(str(v.get("reason", "no reply")).split())[:200]
    return ok, (f"[{flags}] " if flags else "") + reason, model


def run_bucket(base, name, spec, builtin, store, dry):
    existing = builtin.get(name, []) + [e["slogan"] for e in store.get(name, [])]
    # no repeats of anything already on the sign, in any bucket
    seen = {norm(s) for v in builtin.values() for s in v}
    seen |= {norm(e["slogan"]) for v in store.values() for e in v}

    gen_sys = ("You write slogans for a joke-but-sincere yard sign ('IN THIS HOUSE WE "
               "BELIEVE...') owned by an organizational sociologist who studies networks. "
               "Accuracy matters more than cleverness. Reply with a JSON array only.")
    gen_user = (f"Pattern: {spec['pattern']}\n"
                f"Max {MAX_LEN} characters each. Plain ASCII. All lowercase, like the "
                f"examples, except proper names and acronyms.\n\n"
                f"Already on the sign (match this voice, do not repeat or paraphrase):\n"
                + "\n".join(f"- {s}" for s in existing) +
                f"\n\nWrite {PER_BUCKET} new ones. JSON array of objects: "
                '{"slogan": ..., "basis": "the concept/finding, author(s), year"}')
    text, gen_model = chat(base, GENERATOR, gen_sys, gen_user, 1.0)
    cands = []
    for c in json_array(text):
        s, basis = clean(c.get("slogan", "")), printable(" ".join(str(c.get("basis", "")).split()))[:200]
        s = s and decap(s, basis)
        if not s:
            log(f"{name}: reject (format) {str(c.get('slogan'))[:80]!r}")
        elif spec["regex"] and not re.match(spec["regex"], s):
            log(f"{name}: reject (pattern) {s!r}")
        elif norm(s) in seen:
            log(f"{name}: reject (duplicate) {s!r}")
        else:
            seen.add(norm(s))
            cands.append({"slogan": s, "basis": basis})
    if not cands:
        return []

    kept = []
    today = datetime.date.today().isoformat()
    for c in cands:
        ok, reason, ver_model = verify(base, spec, c)
        if ok:
            kept.append({**c, "generator": gen_model, "verifier": ver_model, "date": today})
            log(f"{name}: KEEP {c['slogan']!r} [{c['basis']}] -- {reason}")
        else:
            log(f"{name}: reject (verifier) {c['slogan']!r} [{c['basis']}] -- {reason}")
    if dry:
        for k in kept:
            print(printable(f"  + {name}: {k['slogan']}  [{k['basis']}]"))
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--if-stale", type=float, help="skip unless the last good run is older than this many hours")
    ap.add_argument("--dry-run", action="store_true", help="print survivors; don't write the store")
    ap.add_argument("--bucket", action="append", help="only these buckets")
    args = ap.parse_args()

    if args.if_stale is not None and os.path.exists(STAMP):
        if time.time() - os.path.getmtime(STAMP) < args.if_stale * 3600:
            return
    if not os.path.exists(VK):
        log("no virtual key at ~/.config/llmgw/vk; nothing to do")
        return
    base = gateway()
    if not base:
        log("no gateway reachable; will retry next run")
        return

    builtin = runpy.run_path(os.path.join(HERE, "zen-spacer.py"), run_name="zen_spacer")["YARD_SIGN"]
    try:
        with open(STORE) as f:
            store = json.load(f)
    except (OSError, json.JSONDecodeError):
        store = {}
    for entries in store.values():  # entries from before decap existed
        for e in entries:
            e["slogan"] = decap(e["slogan"], e.get("basis", ""))

    log(f"run on {socket.gethostname()} via {base}: generator {GENERATOR}, verifier {VERIFIER}")
    for name, spec in SPECS.items():
        if args.bucket and name not in args.bucket:
            continue
        try:
            kept = run_bucket(base, name, spec, builtin, store, args.dry_run)
        except Exception as e:  # one bucket failing shouldn't sink the rest
            log(f"{name}: error {type(e).__name__}: {str(e)[:200]}")
            continue
        store[name] = (store.get(name, []) + kept)[-KEEP:]

    if not args.dry_run:
        os.makedirs(CACHE, exist_ok=True)
        write_atomic(STORE, json.dumps(store, indent=1))
        with open(STAMP, "w") as f:
            f.write(datetime.datetime.now().isoformat())


if __name__ == "__main__":
    main()
