#!/usr/bin/env python3
"""Public job board reader (no login, no cookies). Standard library only.

Search (prints: key | title | company | location | date | url):
  python3 scripts/boards.py search vdab revenue-operations marketing-automation
  python3 scripts/boards.py search owlie find-jobs sales marketing operations customer-success
  python3 scripts/boards.py search stepstone marketing-automation crm
  python3 scripts/boards.py search remoteok "marketing operations" revops
  python3 scripts/boards.py search wwr
  python3 scripts/boards.py search landing
  python3 scripts/boards.py search itjobs crm marketing "revenue operations"      (Portugal)
  python3 scripts/boards.py search netempregos marketing crm                       (Portugal)
  python3 scripts/boards.py search vagas crm revops "marketing ops"               (Brazil, max ~10 terms)
  python3 scripts/boards.py search gupy crm revops growth                         (Brazil)
  python3 scripts/boards.py search hellojobs                                      (Macau, browses marketing/IT/casino-marketing areas)
  python3 scripts/boards.py search freelancermap hubspot clay revops              (freelance projects, DACH/remote)
  python3 scripts/boards.py search 99freelas hubspot crm automação                (freelance projects, Brazil)

Any job URL works in detail, including company ATS pages found by web search
(job-boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com): use key "ats:<company>-<id>" with the URL.

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
            raw = r.read()
            enc = "latin-1" if "net-empregos" in url else "utf-8"
            return raw.decode(enc, "replace")
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


# ---- added 2026-09-27: Portugal, Brazil, Macau boards ----
def s_itjobs(terms):
    """ITJobs.pt (Portugal, tech and digital roles)."""
    for t in terms:
        page = get(f"https://www.itjobs.pt/emprego?q={urllib.parse.quote(t)}")
        if not page:
            continue
        for blk in re.split(r'<div class="list-title">', page)[1:]:
            m = re.search(r'href="/oferta/(\d+)/([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
            if not m:
                continue
            comp = re.search(r'class="list-name"><a[^>]*>(.*?)</a>', blk, re.S)
            loc = re.search(r'fa-map-marker"></i>(.*?)&nbsp;&nbsp;', blk, re.S)
            emit(f"itjobs:{m.group(1)}", m.group(3), comp.group(1) if comp else "", loc.group(1) if loc else "", "",
                 f"https://www.itjobs.pt/oferta/{m.group(1)}/{m.group(2)}")


def s_netempregos(terms):
    """Net-Empregos (Portugal, general board; pages are latin-1)."""
    for t in terms:
        page = get(f"https://www.net-empregos.com/pesquisa-empregos.asp?chaves={urllib.parse.quote(t.encode('latin-1', 'ignore'))}")
        if not page:
            continue
        for blk in re.split(r'<h2 style="font-size:20px', page)[1:]:
            m = re.search(r'href=/?(\d+)/([^/> ]+)/?>(.*?)</a>', blk, re.S)
            if not m:
                continue
            date = re.search(r'flaticon-calendar[^>]*></i>\s*([^<]+)<', blk)
            loc = re.search(r'flaticon-pin[^>]*></i>\s*([^<]+)<', blk)
            comp = re.search(r'flaticon-work[^>]*></i>\s*([^<]+)<', blk)
            emit(f"netempregos:{m.group(1)}", m.group(3), comp.group(1) if comp else "", loc.group(1) if loc else "",
                 date.group(1) if date else "", f"https://www.net-empregos.com/{m.group(1)}/{m.group(2)}/")


def s_vagas(terms):
    """Vagas.com.br (Brazil). Rate-limited by Cloudflare: keep it to about 10 terms per run."""
    for t in terms:
        slug = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
        page = get(f"https://www.vagas.com.br/vagas-de-{slug}")
        if not page:
            continue
        for blk in re.split(r'<a class="link-detalhes-vaga"', page)[1:]:
            m = re.search(r'data-id-vaga="(\d+)" title="([^"]*)".*?href="(/vagas/v\d+/[^"]+)"', blk, re.S)
            if not m:
                continue
            comp = re.search(r'class="emprVaga">\s*(.*?)\s*</span>', blk, re.S)
            loc = re.search(r'class="vaga-local">\s*<i[^>]*></i>\s*([^<]+)', blk, re.S)
            date = re.search(r'class="data-publicacao">(?:<i[^>]*></i>)?([^<]+)<', blk)
            emit(f"vagas:{m.group(1)}", m.group(2), comp.group(1) if comp else "", loc.group(1) if loc else "",
                 date.group(1) if date else "", "https://www.vagas.com.br" + m.group(3))


def s_gupy(terms):
    """Gupy portal (Brazil, most large Brazilian employers). Full description is in the search JSON."""
    for t in terms:
        page = get(f"https://portal.gupy.io/job-search/term={urllib.parse.quote(t)}")
        if not page:
            continue
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        if not m:
            log("gupy: no json"); continue
        try:
            jobs = json.loads(m.group(1))["props"]["pageProps"]["initialJobList"]["data"]
        except Exception as e:
            log(f"gupy json {e}"); continue
        for j in jobs:
            loc = ", ".join(x for x in (j.get("city"), j.get("state")) if x) + f" ({j.get('workplaceType', '')})"
            emit(f"gupy:{j['id']}", j.get("name", ""), j.get("careerPageName", ""), loc, (j.get("publishedDate") or "")[:10], j.get("jobUrl", ""))


HJ_AREAS = {"F19": "Marketing and PR", "F29": "IT and Telecom", "F30": "Media and Advertising", "F39": "Casino marketing",
            "F44": "Casino VIP marketing", "F51": "Hotel sales and marketing"}


def s_hellojobs(terms):
    """hello-jobs.com (Macau). Browses the marketing, IT and casino-marketing areas (about 15 newest each); terms are ignored."""
    for code, name in HJ_AREAS.items():
        page = get(f"https://jobsearch.hello-jobs.com/Job-Search/{code[1:]}-Functional-Area-Jobs-in-Macau/{code}.aspx?Lang=ENU")
        if not page:
            continue
        for rel, jid in sorted(set(re.findall(r'href="\.\./([^"]+-Job-Description/[^"]+/(\d+)\.aspx)"', page))):
            title = urllib.parse.unquote(rel.split("/")[-2]).replace("-", " ")
            emit(f"hellojobs:{jid}", title, "", f"Macau ({name})", "", f"https://jobsearch.hello-jobs.com/Job-Search/{rel}")


# ---- added 2026-09-30: freelance and part-time boards ----
def s_freelancermap(terms):
    """freelancermap (DACH freelance projects, many in English and remote). Description is in the search JSON."""
    for t in terms:
        page = get(f"https://www.freelancermap.de/projekte?query={urllib.parse.quote(t)}")
        if not page:
            continue
        m = re.search(r'data-component-name="ProjectSearch"[^>]*>(.*?)</script>', page, re.S)
        if not m:
            log("freelancermap: no json"); continue
        try:
            projects = json.loads(m.group(1)).get("initialResults") or []
        except Exception as e:
            log(f"freelancermap json {e}"); continue
        for pr in projects:
            loc = pr.get("city") or ", ".join(str(x.get("name", x)) if isinstance(x, dict) else str(x) for x in (pr.get("locations") or []))
            extra = " / ".join(x for x in (pr.get("durationText"), pr.get("beginningText"), str(pr.get("budget") or "")) if x)
            emit(f"freelancermap:{pr['id']}", pr.get("title", ""), pr.get("company") or "", f"{loc} ({pr.get('contractType', '')}) {extra}",
                 (pr.get("created") or "")[:10], "https://www.freelancermap.de" + (pr.get("url") or f"/projekt/{pr.get('slug')}"))


def s_99freelas(terms):
    """99freelas (Brazil freelance projects, in Portuguese)."""
    for t in terms:
        page = get(f"https://www.99freelas.com.br/projects?q={urllib.parse.quote(t)}")
        if not page:
            continue
        for slug, title in set(re.findall(r'href="/project/([a-z0-9-]+-\d+)\?fs=t">(.*?)</a>', page)):
            jid = slug.rsplit("-", 1)[1]
            emit(f"99freelas:{jid}", title, "", "Brazil (freelance, remote)", "", f"https://www.99freelas.com.br/project/{slug}")


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
        am = re.match(r"https://jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", url)
        if am:  # Ashby pages are client-rendered: use the public posting API
            api = get(f"https://api.ashbyhq.com/posting-api/job-board/{am.group(1)}")
            try:
                job = next(j for j in json.loads(api or "{}").get("jobs", []) if j.get("id") == am.group(2))
                page = f"<h1>{html.escape(job.get('title', ''))}</h1><p>{html.escape(job.get('location', ''))}</p>" + (job.get("descriptionHtml") or "")
            except (StopIteration, ValueError):
                page = None
        else:
            page = get(url)
        if not page:
            open(fn, "w").write(f"### {key}\n{url}\nNOTEXT\n")
            print(f"{key} NOTEXT (fetch failed or posting closed)"); continue
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
    s.add_argument("board", choices=["vdab", "owlie", "stepstone", "remoteok", "wwr", "landing", "itjobs", "netempregos", "vagas", "gupy", "hellojobs", "freelancermap", "99freelas"])
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
