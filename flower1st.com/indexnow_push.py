#!/usr/bin/env python3
"""
IndexNow 일괄 색인 통보 (빙·네이버·얀덱스·세즈남 공통 수신)

  python indexnow_push.py --make-key
  python indexnow_push.py --check-key --domain 도메인 --key 키
  python indexnow_push.py --domain 도메인 --key 키 --sitemap out\\sitemap.xml --dry-run
  python indexnow_push.py --domain 도메인 --key 키 --sitemap out\\sitemap.xml [--new-only] [--limit N]
"""
import argparse, csv, json, os, secrets, sys, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "indexnow_log.csv")
API = "https://api.indexnow.org/indexnow"


def make_key():
    key = secrets.token_hex(16)  # 32 hex chars
    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{key}.txt")
    open(path, "w", encoding="utf-8").write(key)
    print(f"키: {key}")
    print(f"파일: {path}")
    print('config.json에 "indexnow_key" 값으로 넣으면 build.py가 매 빌드마다 자동으로 이 파일을 재생성합니다.')


def check_key(domain, key):
    url = f"https://{domain}/{key}.txt"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode("utf-8").strip()
            if resp.status == 200 and body == key:
                print(f"[정상] {url}")
                return True
            print(f"[실패] status={resp.status} body={body!r}")
            return False
    except Exception as e:
        print(f"[실패] {url} - {e}")
        return False


def load_sitemap_urls(path):
    tree = ET.parse(path)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text for loc in tree.getroot().findall(".//s:loc", ns)]


def already_sent():
    if not os.path.isfile(LOG):
        return set()
    sent = set()
    for row in csv.DictReader(open(LOG, encoding="utf-8")):
        if row.get("status") in ("200", "202"):
            sent.update(row.get("urls", "").split("|"))
    return sent


def log_result(status, count, detail):
    is_new = not os.path.isfile(LOG)
    with open(LOG, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["timestamp", "count", "status", "detail"])
        w.writerow([datetime.now(timezone.utc).isoformat(), count, status, detail])


def send(domain, key, urls, dry_run, limit):
    if limit:
        urls = urls[:limit]
    if not urls:
        print("보낼 URL 없음 (이미 전부 전송됨 - --new-only)")
        return
    if dry_run:
        print(f"[dry-run] {len(urls)}건 전송 예정")
        for u in urls[:10]:
            print(f"  {u}")
        if len(urls) > 10:
            print(f"  ... 외 {len(urls) - 10}건")
        return

    payload = {
        "host": domain, "key": key,
        "keyLocation": f"https://{domain}/{key}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = str(resp.status)
    except urllib.error.HTTPError as e:
        status = str(e.code)
    except Exception as e:
        status = "error"
        print(f"전송 실패: {e}")

    print(f"응답 코드: {status}  ({len(urls)}건)")
    log_result(status, len(urls), "|".join(urls))
    if status not in ("200", "202"):
        print("200/202가 아니면 403(키 실패)·422(host 불일치)·429(과다요청)를 확인하세요.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-key", action="store_true")
    ap.add_argument("--check-key", action="store_true")
    ap.add_argument("--domain")
    ap.add_argument("--key")
    ap.add_argument("--sitemap")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--new-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if a.make_key:
        return make_key()

    if a.check_key:
        if not (a.domain and a.key):
            sys.exit("--check-key는 --domain --key 필요")
        return check_key(a.domain, a.key)

    if not a.sitemap:
        sys.exit("--sitemap 경로 필요 (또는 --make-key / --check-key)")
    if not (a.domain and a.key):
        sys.exit("--domain --key 필요")

    urls = load_sitemap_urls(a.sitemap)
    if a.new_only:
        sent = already_sent()
        urls = [u for u in urls if u not in sent]
    send(a.domain, a.key, urls, a.dry_run, a.limit)


if __name__ == "__main__":
    main()
