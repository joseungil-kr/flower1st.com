#!/usr/bin/env python3
"""빌드 검증: URL수/중복/깨진링크/사이트맵 정합성/얇은 페이지 비율/분량/용량"""
import os, re, csv, gzip, json
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
C = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))


def main():
    dirs = [d for d in os.listdir(OUT) if os.path.isdir(os.path.join(OUT, d)) and d != "assets"]
    pages = {d: open(os.path.join(OUT, d, "index.html"), encoding="utf-8").read() for d in dirs}
    pages[""] = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()

    rows = list(csv.DictReader(open(os.path.join(ROOT, "facilities.csv"), encoding="utf-8")))
    sidos = {r["sido"] for r in rows}
    sggs = {(r["sido"], r["sigungu"]) for r in rows if r["sido"] != r["sigungu"]}
    crem_path = os.path.join(ROOT, "crematorium.csv")
    crem_sidos = {r["sido"] for r in csv.DictReader(open(crem_path, encoding="utf-8"))} if os.path.isfile(crem_path) else set()

    expected = 1 + len(sidos) + len(sggs) + len(rows) + len(crem_sidos)
    print(f"[URL 수]        생성 {len(pages)}  기대 {expected}  {'OK' if len(pages)==expected else 'FAIL'}")

    dup = [d for d, c in Counter(dirs).items() if c > 1]
    print(f"[중복 폴더]      {len(dup)}건  {'OK' if not dup else dup[:5]}")

    broken = []
    href_re = re.compile(r"href=['\"]/([^'\"]*)/['\"]")
    for slug, html_text in pages.items():
        for m in href_re.finditer(html_text):
            target = urllib_unquote(m.group(1))
            if target and target not in pages:
                broken.append((slug, target))
    print(f"[깨진 내부링크]   {len(broken)}건  {'OK' if not broken else broken[:5]}")

    sm = open(os.path.join(OUT, "sitemap.xml"), encoding="utf-8").read()
    sm_count = sm.count("<url>")
    print(f"[sitemap 수]     sitemap {sm_count}  실제파일 {len(pages)}  {'OK' if sm_count==len(pages) else 'FAIL'}")

    thin = sum(1 for r in rows if not (r.get("address") or "").strip())
    pct = thin / len(rows) * 100
    print(f"[address 결측]   {thin}/{len(rows)} = {pct:.1f}%  {'OK' if pct<=30 else 'WARN 30% 초과'}")

    fac_pages = [(d, t) for d, t in pages.items() if d.endswith(KW_of(C))]
    sizes = [len(t.encode('utf-8')) for _, t in fac_pages]
    gz = [len(gzip.compress(t.encode('utf-8'))) for _, t in fac_pages]
    words = [len(strip_tags(t).split()) for _, t in fac_pages]
    if sizes:
        print(f"[시설 페이지 용량] raw 평균 {sum(sizes)//len(sizes)}B  gzip 평균 {sum(gz)//len(gz)}B  (사양 10KB는 gzip 기준으로 해석)")
        print(f"[시설 페이지 분량] 평균 {sum(words)//len(words)} 토큰  최소 {min(words)}  최대 {max(words)}  (사양 1500~2300)")


def KW_of(c):
    return c["primary_kw"]


def strip_tags(t):
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return html_unescape(t)


def html_unescape(t):
    import html as h
    return h.unescape(t)


def urllib_unquote(s):
    import urllib.parse
    return urllib.parse.unquote(s)


if __name__ == "__main__":
    main()
