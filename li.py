#!/usr/bin/env python3
"""LinkedIn public job search (guest endpoints, no login). Standard library only.

Search (prints: id | title | company | location | posted date):
  python3 scripts/li.py search "revenue operations" "Porto, Portugal" --days 3
  python3 scripts/li.py search "GTM engineer" "European Union" --days 3 --remote

Fetch full descriptions (one .txt per id in --out):
  python3 scripts/li.py detail 4370672271 4413028604 --out jobs-cache
"""
import argparse, html, os, re, sys, time, urllib.parse, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE = "https://www.linkedin.com/jobs-guest/jobs/api"


def get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.5"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(5 * (attempt + 1))  # back off on 429 / transient errors


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def grab(text, pattern):
    m = re.search(pattern, text, re.S)
    return clean(m.group(1)) if m else ""


def search(keywords, location, days, remote, pages):
    q = {"keywords": keywords, "location": location, "f_TPR": f"r{days * 86400}", "sortBy": "DD"}
    if remote:
        q["f_WT"] = "2"
    seen = set()
    for p in range(pages):
        page = get(f"{BASE}/seeMoreJobPostings/search?{urllib.parse.urlencode(q)}&start={p * 10}")
        if not page:
            break
        cards = [c for c in page.split("<li>") if re.search(r"jobPosting:(\d+)", c)]
        if not cards:
            break
        for c in cards:
            jid = re.search(r"jobPosting:(\d+)", c).group(1)
            if jid in seen:
                continue
            seen.add(jid)
            title = grab(c, r"base-search-card__title[^>]*>(.*?)</h3>")
            company = grab(c, r"base-search-card__subtitle[^>]*>(.*?)</h4>")
            loc = grab(c, r"job-search-card__location[^>]*>(.*?)</span>")
            d = re.search(r'datetime="([^"]+)"', c)
            print(f"{jid} | {title} | {company} | {loc} | {d.group(1) if d else ''}")
        time.sleep(1.2)


def detail(ids, out):
    os.makedirs(out, exist_ok=True)
    for jid in ids:
        try:
            page = get(f"{BASE}/jobPosting/{jid}")
            if not page:
                print(f"{jid} NOT FOUND (closed or removed)")
                continue
            title = grab(page, r"top-card-layout__title[^>]*>(.*?)</h2>")
            company = grab(page, r"topcard__org-name-link[^>]*>(.*?)</a>")
            loc = grab(page, r"topcard__flavor--bullet[^>]*>(.*?)</span>")
            crit = " / ".join(f"{clean(a)}: {clean(b)}" for a, b in re.findall(
                r"description__job-criteria-subheader[^>]*>(.*?)</h3>\s*<span[^>]*>(.*?)</span>", page, re.S))
            closed = "No longer accepting applications" in page
            m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", page, re.S)
            desc = m.group(1) if m else ""
            desc = re.sub(r"<br\s*/?>", "\n", desc)
            desc = re.sub(r"</(p|li|ul|ol|h\d)>", "\n", desc)
            desc = desc.replace("<li>", "- ")
            desc = html.unescape(re.sub(r"<[^>]+>", "", desc))
            desc = re.sub(r"(\n\s*){3,}", "\n\n", desc)
            text = f"### {title} | {company} | {loc}\n{crit}\n{'CLOSED: no longer accepting applications' if closed else ''}\nhttps://www.linkedin.com/jobs/view/{jid}\n\n{desc}"
            path = os.path.join(out, f"{jid}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"{jid} ok {len(text)} chars | {title} | {company}{' | CLOSED' if closed else ''}")
        except Exception as e:  # keep going on individual failures
            print(f"{jid} ERR {e}")
        time.sleep(1.2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("keywords")
    s.add_argument("location")
    s.add_argument("--days", type=int, default=3)
    s.add_argument("--remote", action="store_true")
    s.add_argument("--pages", type=int, default=2)
    d = sub.add_parser("detail")
    d.add_argument("ids", nargs="+")
    d.add_argument("--out", default="jobs-cache")
    a = ap.parse_args()
    if a.cmd == "search":
        search(a.keywords, a.location, a.days, a.remote, a.pages)
    else:
        detail(a.ids, a.out)
    sys.stdout.flush()
