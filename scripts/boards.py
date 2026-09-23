#!/usr/bin/env python3
"""Public job board reader (no login, no cookies). Standard library only.

Search (prints: key | title | company | location | date | url):
  python3 scripts/boards.py search vdab revenue-operations marketing-automation
  python3 scripts/boards.py search owlie find-jobs sales marketing operations customer-success
  python3 scripts/boards.py search stepstone marketing-automation crm
  python3 scripts/boards.py search remoteok "marketing operations" revops
  python3 scripts/boards.py search wwr
  python3 scripts/boards.py search landing

Fetch full text of postings (one .txt per key in --out; NOTEXT if client-rendered):
  python3 scripts/boards.py detail "owlie:growth-marketeer-b2b|https://www.owliejobs.com/job-postings/growth-marketeer-b2b" --out /tmp/jobs
  (argument is key|url; the key alone works for vdab/owlie/landing/remoteok/wwr)

Board hits that fail or return an unexpected page are logged to stderr, never fatal.
"""
import argparse, hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PAUSE = 2.0
_last = {}


def get(url):
    dom = urllib.parse.urlparse(url).netloc
    wait = PAUSE - (time.time() - _last.get(dom, 0))
    if wait > 0:
        time.sleep(wait)
    _last[dom] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.7,nl;q=0.5",
                                               "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        log(f"HTTP {e.code} {url}")
    except Exception as e:
        log(f"ERR {e} {url}")
    return None


def log(msg):
    print(f"# {msg}", file=sys.stderr)


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def text_of(page):
    page = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>", "\n", page)
    page = re.sub(r"(?i)</(p|li|ul|ol|h\d|div|tr)>", "\n", page)
    page = re.sub(r"(?i)<li[^>]*>", "- ", page)
    t = html.unescape(re.sub(r"<[^>]+>", " ", page))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"(\n\s*){3,}", "\n\n", t).strip()


def emit(key, title, company, loc, date, url):
    print(" | ".join(clean(x).replace("|", "/") for x in (key, title, company, loc, date, url)))


# ---------- search ----------
def s_vdab(terms):
    for t in terms:
        slug = t.lower().strip().replace(" ", "-")
        page = get(f"https://www.vdab.be/vindeenjob/jobs/{slug}")
        if not page:
            continue
        tiles = page.split('class="product-tile"')[1:]
        if not tiles:
            log(f"vdab {slug}: 0 tiles")
        for tile in tiles:
            m = re.search(r"/vindeenjob/vacatures/(\d+)/([a-z0-9-]+)", tile)
            if not m:
                continue
            title = re.search(r'product-title[^>]*>(.*?)</h2>', tile, re.S)
            loc = re.search(r'location-job[^>]*>(.*?)</div>', tile, re.S)
            strongs = re.findall(r"<strong>(.*?)</strong>", loc.group(1), re.S) if loc else []
            date = re.search(r'online-sinds[^>]*>(.*?)<', tile, re.S)
            emit(f"vdab:{m.group(1)}", title.group(1) if title else m.group(2), strongs[0] if strongs else "",
                 strongs[1] if len(strongs) > 1 else "", date.group(1) if date else "",
                 f"https://www.vdab.be/vindeenjob/vacatures/{m.group(1)}/{m.group(2)}")


def s_owlie(terms):
    seen = set()
    for t in terms:
        base = "https://www.owliejobs.com/find-jobs" if t in ("find-jobs", "all") else f"https://www.owliejobs.com/main-categories/{t}"
        url, pageno = base, 1
        while url and pageno <= 15:
            page = get(url)
            if not page:
                break
            chunks = page.split('fs-list-field="title"')[1:]
            new = 0
            for c in chunks:
                title = re.search(r"^[^>]*>([^<]+)", c)
                href = re.search(r'href="/job-postings/([a-z0-9-]+)"', c)
                if not href or href.group(1) in seen:
                    continue
                seen.add(href.group(1)); new += 1
                comp = re.search(r'fs-list-field="company"[^>]*>([^<]*)', c)
                city = re.search(r'fs-list-field="city"[^>]*>([^<]*)', c)
                emit(f"owlie:{href.group(1)}", title.group(1) if title else href.group(1), comp.group(1) if comp else "",
                     city.group(1) if city else "", "", f"https://www.owliejobs.com/job-postings/{href.group(1)}")
            nxt = re.search(r'href="(\?[a-z0-9]+_page=(\d+))"[^>]*(?:w-pagination-next|aria-label="Next)', page)
            if not nxt:
                cands = [m for m in re.findall(r'\?([a-z0-9]+)_page=(\d+)', page) if int(m[1]) == pageno + 1]
                nxt_q = f"?{cands[0][0]}_page={cands[0][1]}" if cands else None
            else:
                nxt_q = nxt.group(1)
            if not nxt_q or new == 0:
                break
            pageno += 1
            url = base + nxt_q


def s_stepstone(terms):
    for t in terms:
        slug = t.lower().strip().replace(" ", "-")
        page = get(f"https://www.stepstone.be/jobs/{slug}")
        if not page:
            continue
        items = page.split('data-at="job-item"')[1:]
        if not items:
            log(f"stepstone {slug}: 0 items")
        for it in items:
            m = re.search(r'href="(/[^"]*--(\d+)-inline\.html)"', it)
            if not m:
                continue
            title = re.search(r'data-at="job-item-title"[^>]*>(.*?)</a>', it, re.S)
            comp = re.search(r'data-at="job-item-company-name"[^>]*>(.*?)</(?:span|div|a)>', it, re.S)
            loc = re.search(r'data-at="job-item-location"[^>]*>(.*?)</(?:span|div)>', it, re.S)
            ago = re.search(r'data-at="job-item-timeago"[^>]*>(.*?)</(?:span|div)>', it, re.S)
            tt = clean(re.sub(r"(?is)<style.*?</style>", "", title.group(1))) if title else m.group(1)
            emit(f"stepstone:{m.group(2)}", tt, clean(re.sub(r"(?is)<style.*?</style>", "", comp.group(1))) if comp else "",
                 clean(re.sub(r"(?is)<style.*?</style>", "", loc.group(1))) if loc else "",
                 clean(re.sub(r"(?is)<style.*?</style>", "", ago.group(1))) if ago else "",
                 "https://www.stepstone.be" + m.group(1))


def s_remoteok(terms):
    page = get("https://remoteok.com/api")
    if not page:
        return
    try:
        data = [d for d in json.loads(page) if isinstance(d, dict) and d.get("id")]
    except Exception as e:
        log(f"remoteok json {e}"); return
    pats = [t.lower() for t in terms] or [""]
    for d in data:
        blob = (d.get("position", "") + " " + " ".join(d.get("tags") or [])).lower()
        if any(p in blob for p in pats):
            emit(f"remoteok:{d['id']}", d.get("position", ""), d.get("company", ""), d.get("location", ""),
                 (d.get("date") or "")[:10], d.get("url") or f"https://remoteok.com/remote-jobs/{d['id']}")


def s_wwr(terms):
    page = get("https://weworkremotely.com/categories/remote-sales-and-marketing-jobs")
    if not page:
        return
    seen = set()
    for li in page.split("<li")[1:]:
        m = re.search(r'href="/remote-jobs/([a-z0-9-]+)"', li)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        title = re.search(r'class="new-listing__header__title[^"]*"[^>]*>(.*?)</', li, re.S) or re.search(r'class="title"[^>]*>(.*?)</', li, re.S)
        comp = re.search(r'class="new-listing__company-name[^"]*"[^>]*>(.*?)</', li, re.S) or re.search(r'class="company"[^>]*>(.*?)</', li, re.S)
        reg = re.search(r'class="new-listing__company-headquarters[^"]*"[^>]*>(.*?)</', li, re.S) or re.search(r'class="region[^"]*"[^>]*>(.*?)</', li, re.S)
        emit(f"wwr:{m.group(1)}", title.group(1) if title else m.group(1), comp.group(1) if comp else "",
             reg.group(1) if reg else "", "", f"https://weworkremotely.com/remote-jobs/{m.group(1)}")


def s_landing(terms):
    for p in range(1, 6):
        page = get(f"https://landing.jobs/jobs?page={p}")
        if not page:
            break
        m = re.search(r'<script id="initial-search-results" type="application/json">(.*?)</script>', page, re.S)
        if not m:
            log("landing: no json"); break
        try:
            d = json.loads(m.group(1))
        except Exception as e:
            log(f"landing json {e}"); break
        for o in d.get("offers", []):
            locs = "; ".join(x.get("label") or "" for x in o.get("office_locations") or []) or o.get("location") or ""
            if o.get("full_remote"):
                locs += " (remote)"
            emit(f"landing:{o['id']}", o.get("title", ""), o.get("company_name", ""), locs, o.get("published_at", "") or "",
                 f"https://landing.jobs/at/{o.get('company_slug')}/{o.get('slug')}")
        if d.get("last_page?", True):
            break


# ---------- detail ----------
def detail(items, out):
    os.makedirs(out, exist_ok=True)
    for it in items:
        key, _, url = it.partition("|")
        board, _, ident = key.partition(":")
        if not url:
            url = {"owlie": f"https://www.owliejobs.com/job-postings/{ident}",
                   "remoteok": f"https://remoteok.com/remote-jobs/{ident}",
                   "wwr": f"https://weworkremotely.com/remote-jobs/{ident}"}.get(board, "")
        fn = os.path.join(out, re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".txt")
        if board == "vdab" or not url:
            open(fn, "w").write(f"### {key}\n{url}\nNOTEXT\n")
            print(f"{key} NOTEXT (client-rendered)"); continue
        page = get(url)
        if not page:
            open(fn, "w").write(f"### {key}\n{url}\nNOTEXT\n")
            print(f"{key} NOTEXT (fetch failed)"); continue
        body = page
        if board == "owlie":
            m = re.search(r'(?is)<main.*?</main>', page)
            body = m.group(0) if m else page
        t = text_of(body)
        closed = bool(re.search(r"(?i)(no longer (available|accepting)|vacature is (verlopen|niet meer)|this job (has expired|is closed))", t))
        if len(t) < 400:
            open(fn, "w").write(f"### {key}\n{url}\nNOTEXT\n")
            print(f"{key} NOTEXT (short page)"); continue
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"### {key}\nPosted: unknown | Applicants: unknown{' | CLOSED' if closed else ''}\n{url}\n\n{t[:20000]}")
        print(f"{key} ok {len(t)} chars{' | CLOSED' if closed else ''}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("board", choices=["vdab", "owlie", "stepstone", "remoteok", "wwr", "landing"])
    s.add_argument("terms", nargs="*")
    d = sub.add_parser("detail")
    d.add_argument("items", nargs="+")
    d.add_argument("--out", default="jobs-cache")
    a = ap.parse_args()
    if a.cmd == "search":
        try:
            globals()["s_" + a.board](a.terms)
        except Exception as e:
            log(f"{a.board} failed: {e}")
    else:
        detail(a.items, a.out)
    sys.stdout.flush()
