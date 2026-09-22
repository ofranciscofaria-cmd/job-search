#!/usr/bin/env python3
"""Public job board reader (no login, no cookies). Standard library only.

Search (prints: key | title | company | location | date | url):
  python3 scripts/boards.py search vdab revenue-operations marketing-automation
  python3 scripts/boards.py search owlie sales marketing operations customer-success
  python3 scripts/boards.py search stepstone marketing-automation crm
  python3 scripts/boards.py search remoteok "marketing operations" revops
  python3 scripts/boards.py search wwr
  python3 scripts/boards.py search landing marketing growth
  python3 scripts/boards.py search wttj growth   (usually blocked: client-rendered)
  python3 scripts/boards.py search wellfound x   (usually blocked: Cloudflare)

Detail (one .txt per key in --out; writes NOTEXT when the page is client-rendered):
  python3 scripts/boards.py detail --out /tmp/jobs "owlie:<slug>|<url>" "vdab:<id>|<url>"
  Each argument is "<key>|<url>" (key alone works for owlie/vdab/stepstone/landing if url unknown).

Polite: browser User-Agent, 2 s pause between requests (never more than 1 req/s per domain).
Defensive: a board that fails or returns an unexpected page logs to stderr and returns 0 hits.
"""
import argparse, hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PAUSE = 2.0
_last = {}


def log(msg):
    print(f"[boards] {msg}", file=sys.stderr)


def get(url, accept="text/html,application/json"):
    dom = urllib.parse.urlparse(url).netloc
    wait = PAUSE - (time.time() - _last.get(dom, 0))
    if wait > 0:
        time.sleep(wait)
    _last[dom] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.7,nl;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
            body = r.read().decode("utf-8", "replace")
            if code != 200:
                log(f"HTTP {code} {url}")
                return None
            return body
    except urllib.error.HTTPError as e:
        log(f"HTTP {e.code} {url}")
    except Exception as e:  # DNS, proxy 403 on CONNECT, timeouts
        log(f"ERROR {type(e).__name__}: {e} {url}")
    return None


def clean(s):
    s = re.sub(r"<(script|style|svg|noscript)\b.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def one(s):
    return re.sub(r"\s+", " ", clean(s)).strip()


def emit(hits, key, title, company, location, date, url, seen):
    if key in seen:
        return
    seen.add(key)
    row = [key, title, company, location, date, url]
    hits.append(row)
    print(" | ".join((x or "").replace("|", "/") for x in row), flush=True)


def slugify(k):
    return re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-")


# ---------- VDAB ----------
def s_vdab(keywords, seen):
    hits = []
    for kw in keywords:
        url = f"https://www.vdab.be/vindeenjob/jobs/{slugify(kw)}"
        page = get(url)
        if not page:
            continue
        tiles = page.split('class="product-tile"')[1:]
        if not tiles:
            log(f"vdab: 0 tiles for {kw}")
        for t in tiles:
            m = re.search(r"/vindeenjob/vacatures/(\d+)/([a-z0-9-]+)", t)
            if not m:
                continue
            jid, slug = m.groups()
            title = one(re.search(r'class="product-title"[^>]*>(.*?)</h2>', t, re.S).group(1)) if 'product-title' in t else slug
            loc = re.search(r'class="location-job"[^>]*>(.*?)</div>', t, re.S)
            strongs = re.findall(r"<strong>(.*?)</strong>", loc.group(1), re.S) if loc else []
            company = one(strongs[0]) if strongs else ""
            city = one(strongs[1]) if len(strongs) > 1 else ""
            d = re.search(r'online-sinds">\s*Online sinds\s*(.*?)<', t, re.S)
            emit(hits, f"vdab:{jid}", title, company, city, one(d.group(1)) if d else "",
                 f"https://www.vdab.be/vindeenjob/vacatures/{jid}/{slug}", seen)
    return hits


# ---------- Owlie ----------
def _owlie_parse(page, hits, seen):
    n = 0
    for blk in re.split(r'(?=<div[^>]*fs-list-field="title")', page)[1:]:
        f = {k: one(v) for k, v in re.findall(r'fs-list-field="(\w+)"[^>]*>(.*?)</div>', blk[:6000], re.S)}
        m = re.search(r'href="/job-postings/([a-z0-9-]+)"', blk[:8000])
        if not m:
            continue
        slug = m.group(1)
        n += 1
        loc = " ".join(x for x in [f.get("city", ""), f.get("type", "")] if x)
        emit(hits, f"owlie:{slug}", f.get("title", slug), f.get("company", ""), loc, f.get("level", ""),
             f"https://www.owliejobs.com/job-postings/{slug}", seen)
    return n


def s_owlie(categories, seen):
    hits = []
    urls = ["https://www.owliejobs.com/find-jobs"] + [f"https://www.owliejobs.com/main-categories/{c}" for c in categories]
    for base in urls:
        page = get(base)
        if not page:
            continue
        n = _owlie_parse(page, hits, seen)
        pager = re.search(r'\?([0-9a-f]+_page)=2', page)
        p = 2
        while pager and n and p <= 15:
            nxt = get(f"{base}?{pager.group(1)}={p}")
            if not nxt:
                break
            n = _owlie_parse(nxt, hits, seen)
            if not re.search(rf'{pager.group(1)}={p + 1}', nxt):
                break
            p += 1
    return hits


# ---------- StepStone Belgium ----------
def s_stepstone(keywords, seen):
    hits = []
    for kw in keywords:
        for url in (f"https://www.stepstone.be/jobs/{slugify(kw)}", f"https://www.stepstone.be/en/jobs/{slugify(kw)}"):
            page = get(url)
            if not page:
                continue
            found = 0
            for m in re.finditer(r'"title":"((?:[^"\\]|\\.)*)","url":"(https://www\.stepstone\.be/[^"]*?--(\d+)-inline\.html)[^"]*"', page):
                title, jurl, jid = json.loads(f'"{m.group(1)}"'), m.group(2), m.group(3)
                win = page[m.end(): m.end() + 2500]
                comp = re.search(r'"companyName":"((?:[^"\\]|\\.)*)"', win)
                date = re.search(r'"datePosted":"([0-9-]{10})', win)
                loc = re.search(r'"location":"((?:[^"\\]|\\.)*)"', win) or re.search(r'"location":"((?:[^"\\]|\\.)*)"', page[max(0, m.start() - 2500): m.start()])
                emit(hits, f"stepstone:{jid}", title, json.loads(f'"{comp.group(1)}"') if comp else "",
                     json.loads(f'"{loc.group(1)}"') if loc else "", date.group(1) if date else "", jurl, seen)
                found += 1
            if not found:
                for jurl, jid in re.findall(r'(https://www\.stepstone\.be/jobs--[^"?]*?--(\d+)-inline\.html)', page):
                    parts = jurl.split("jobs--", 1)[1].rsplit("--", 1)[0].split("-")
                    emit(hits, f"stepstone:{jid}", " ".join(parts), "", "", "", jurl, seen)
                    found += 1
            if found:
                break
            log(f"stepstone: 0 hits for {kw} at {url}")
    return hits


# ---------- RemoteOK ----------
def s_remoteok(keywords, seen):
    hits = []
    page = get("https://remoteok.com/api", accept="application/json")
    if not page:
        return hits
    try:
        data = json.loads(page)
    except ValueError:
        log("remoteok: bad JSON")
        return hits
    kws = [k.lower() for k in keywords]
    for j in data:
        if not isinstance(j, dict) or "id" not in j:
            continue
        hay = " ".join([j.get("position", ""), " ".join(j.get("tags") or [])]).lower()
        if kws and not any(k in hay for k in kws):
            continue
        emit(hits, f"remoteok:{j['id']}", j.get("position", ""), j.get("company", ""), j.get("location", "") or "Remote",
             (j.get("date") or "")[:10], j.get("url") or f"https://remoteok.com/remote-jobs/{j['id']}", seen)
    return hits


# ---------- We Work Remotely ----------
def s_wwr(keywords, seen):
    hits = []
    page = get("https://weworkremotely.com/categories/remote-sales-and-marketing-jobs")
    if not page:
        return hits
    kws = [k.lower() for k in keywords]
    for li in page.split("<li")[1:]:
        m = re.search(r'href="(/remote-jobs/([a-z0-9-]+))"', li)
        if not m or "find-your-plan" in m.group(1):
            continue
        title = re.search(r'class="new-listing__header__title[^"]*"[^>]*>(.*?)</', li, re.S) or re.search(r'class="title"[^>]*>(.*?)</', li, re.S)
        comp = re.search(r'class="new-listing__company-name[^"]*"[^>]*>(.*?)</', li, re.S) or re.search(r'class="company"[^>]*>(.*?)</', li, re.S)
        region = re.search(r'class="new-listing__company-headquarters[^"]*"[^>]*>(.*?)</', li, re.S) or re.search(r'class="region[^"]*"[^>]*>(.*?)</', li, re.S)
        t = one(title.group(1)) if title else m.group(2)
        if kws and not any(k in t.lower() for k in kws):
            continue
        cats = " / ".join(one(x) for x in re.findall(r'class="new-listing__categories__category"[^>]*>(.*?)</', li, re.S))
        key = f"wwr:{m.group(2)}"
        emit(hits, key, t, one(comp.group(1)) if comp else "", " ".join(x for x in [one(region.group(1)) if region else "", cats] if x),
             "", "https://weworkremotely.com" + m.group(1), seen)
    return hits


# ---------- Landing.jobs (Portugal tech) ----------
def s_landing(keywords, seen):
    hits = []
    for kw in keywords or [""]:
        url = "https://landing.jobs/jobs" + (f"?q={urllib.parse.quote(kw)}" if kw else "")
        page = get(url)
        if not page:
            continue
        m = re.search(r'<script id="initial-search-results" type="application/json">(.*?)</script>', page, re.S)
        if not m:
            log(f"landing: no JSON for {kw}")
            continue
        try:
            offers = json.loads(m.group(1)).get("offers", [])
        except ValueError:
            log("landing: bad JSON")
            continue
        for o in offers:
            locs = ", ".join(x.get("label", "") for x in o.get("office_locations") or []) or o.get("location", "")
            if o.get("full_remote"):
                locs = (locs + " (remote)").strip()
            emit(hits, f"landing:{o.get('id')}", o.get("title", ""), o.get("company_name", ""), locs, o.get("published_at", ""),
                 f"https://landing.jobs/at/{o.get('company_slug')}/{o.get('slug')}", seen)
    return hits


def s_blocked(name, url):
    def run(keywords, seen):
        page = get(url)
        if not page:
            log(f"{name}: blocked or client-rendered ({url}); use WebSearch instead")
        else:
            log(f"{name}: page is client-rendered (JS/Cloudflare); no parser, use WebSearch instead")
        return []
    return run


BOARDS = {
    "vdab": s_vdab, "owlie": s_owlie, "stepstone": s_stepstone, "remoteok": s_remoteok, "wwr": s_wwr, "landing": s_landing,
    "wttj": s_blocked("wttj", "https://www.welcometothejungle.com/en/jobs"),
    "wellfound": s_blocked("wellfound", "https://wellfound.com/jobs"),
}


# ---------- detail ----------
def default_url(key):
    b, _, v = key.partition(":")
    if b == "owlie":
        return f"https://www.owliejobs.com/job-postings/{v}"
    if b == "vdab":
        return f"https://www.vdab.be/vindeenjob/vacatures/{v}"
    if b == "remoteok":
        return f"https://remoteok.com/remote-jobs/{v}"
    if b == "wwr":
        return f"https://weworkremotely.com/remote-jobs/{v}"
    return None


def extract(key, url, page):
    b = key.split(":", 1)[0]
    if b == "vdab":
        return None  # client-rendered: confirm elsewhere
    if b == "owlie":
        m = re.search(r'<main\b.*?</main>', page, re.S)
        return clean(m.group(0) if m else page)
    if b == "stepstone":
        ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        for blob in ld:
            try:
                d = json.loads(blob)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("@type") == "JobPosting":
                org = (d.get("hiringOrganization") or {}).get("name", "")
                return f"{d.get('title','')}\n{org}\nPosted: {d.get('datePosted','')[:10]}\n\n" + clean(d.get("description", ""))
        m = re.search(r'<article\b.*?</article>', page, re.S)
        return clean(m.group(0)) if m else None
    if b == "landing":
        m = re.search(r'<main\b.*?</main>', page, re.S)
        return clean(m.group(0) if m else page)
    txt = clean(re.search(r'<body\b.*?</body>', page, re.S).group(0) if "<body" in page else page)
    return txt if len(txt) > 400 else None


def detail(items, out):
    os.makedirs(out, exist_ok=True)
    for it in items:
        key, _, url = it.partition("|")
        url = url or default_url(key)
        fn = os.path.join(out, re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".txt")
        if not url:
            log(f"{key}: no url")
            continue
        page = get(url)
        closed = page is None or bool(re.search(r"(no longer available|niet langer beschikbaar|vacature is afgesloten|position has been filled|job has expired)", page or "", re.I))
        text = extract(key, url, page) if page else None
        with open(fn, "w") as f:
            f.write(f"Key: {key}\nURL: {url}\n")
            if page is None:
                f.write("CLOSED (page not reachable)\n")
            elif closed:
                f.write("CLOSED\n")
            f.write("\n" + (text if text else "NOTEXT") + "\n")
        print(f"{key} -> {fn}{' NOTEXT' if not text else ''}{' CLOSED' if closed else ''}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("board", choices=sorted(BOARDS))
    s.add_argument("keywords", nargs="*")
    d = sub.add_parser("detail")
    d.add_argument("items", nargs="+")
    d.add_argument("--out", default="jobs-cache")
    a = ap.parse_args()
    if a.cmd == "search":
        hits = BOARDS[a.board](a.keywords, set())
        log(f"{a.board}: {len(hits)} hits")
    else:
        detail(a.items, a.out)


if __name__ == "__main__":
    main()
