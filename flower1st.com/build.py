#!/usr/bin/env python3
"""
시설 단위 지역 키워드 사이트 생성기  (화환 3개 업종 공용)

  config.json + facilities.csv (+ crematorium.csv)  ->  out/   (Cloudflare Pages 업로드용)

  /                        전국 허브 (시도 목록)
  /{시도}{시설명사}/         시도 허브
  /{시군구}{시설명사}/       시군구 허브
  /{시설명}{핵심어}/         시설 페이지  ← 검색어 완전일치, 시설당 1개
  /{시도}화장시설안내/        화장시설 시도 허브 (crematorium.csv 있을 때만, 시설 단위 페이지 없음)
  /sitemap.xml /robots.txt

  페이지 구조·순서는 claude/구조사양서.md §2·§3을 따른다.

업종 전환은 config.json 한 개만 교체:
  장례  facility_noun=장례식장  primary_kw=화환   alt=근조화환/장례식화환/부고화환
  개업  facility_noun=전통시장  primary_kw=개업화환 alt=축하화환/화환
  결혼  facility_noun=예식장    primary_kw=결혼식화환 alt=축하화환/화환

  ribbons/bugo_url은 config에 없으면 해당 블록을 렌더하지 않는다 (버티컬별 선택 콘텐츠).

  python3 build.py            전체
  python3 build.py --stage 1  시설 페이지 30%만 (단계 발행 실험용)
"""
import json, csv, os, shutil, argparse, html, urllib.parse, hashlib
from collections import OrderedDict
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
C = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
FN, KW = C["facility_noun"], C["primary_kw"]
ALT = C.get("alt_kws", [])
POOL_PATH = os.path.join(ROOT, "content_pool.json")
POOL = json.load(open(POOL_PATH, encoding="utf-8")) if os.path.isfile(POOL_PATH) else {}

def pick(pool_name, key, salt):
    """이름+salt 해시로 pool에서 결정적으로 하나 고른다 (재빌드해도 같은 시설은 항상 같은 문구)."""
    pool = POOL.get(pool_name)
    if not pool:
        return None
    h = hashlib.md5(f"{key}:{salt}".encode("utf-8")).hexdigest()
    return pool[int(h, 16) % len(pool)]

def esc(s): return html.escape(str(s or ""), quote=True)
def enc(p): return urllib.parse.quote(p, safe="/")
def has(r, k): return bool((r.get(k) or "").strip())
def positive(r, k):  # 0은 "있다"고 서술하면 안 되는 수치 항목(주차/빈소/안치)에 사용
    v = (r.get(k) or "").strip()
    return v.isdigit() and int(v) > 0

SGG_SLUG = {}  # (sido, sigungu) -> URL slug, 시도 간 동명 시군구는 시도명을 붙여 충돌 회피
def sgg_slug(sido, sgg): return SGG_SLUG.get((sido, sgg), sgg + FN)

def load():
    rows = [r for r in csv.DictReader(open(os.path.join(ROOT, "facilities.csv"), encoding="utf-8"))
            if (r.get("name") or "").strip()]
    tree = OrderedDict()
    for r in rows:
        tree.setdefault(r["sido"], OrderedDict()).setdefault(r["sigungu"], []).append(r)
    return tree, rows

def load_crematorium():
    path = os.path.join(ROOT, "crematorium.csv")
    if not os.path.isfile(path):
        return OrderedDict()
    tree = OrderedDict()
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if (r.get("name") or "").strip():
            tree.setdefault(r["sido"], []).append(r)
    return tree

def og_image():
    img = C.get("og_image")
    if not img:
        return ""
    url = f"https://{C['domain']}{img}"
    return f'<meta property="og:image" content="{esc(url)}">'

def favicon_tags():
    if not os.path.isdir(os.path.join(ROOT, "assets")):
        return ""
    return ('<link rel="icon" href="/assets/favicon.png" type="image/png">'
            '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">')

def site_verification_tags():
    tags = []
    if C.get("naver_site_verification"):
        tags.append(f'<meta name="naver-site-verification" content="{esc(C["naver_site_verification"])}">')
    if C.get("google_site_verification"):
        tags.append(f'<meta name="google-site-verification" content="{esc(C["google_site_verification"])}">')
    return "".join(tags)

# ---------------- 셸 ----------------
def shell(title, desc, canon, body, extra_head=""):
    a = C["accent"]
    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="{esc(C['brand'])}">
{og_image()}
{favicon_tags()}
{extra_head}
<meta name="theme-color" content="{a}">
<link rel="stylesheet" href="/assets/style.css">
<style>:root{{--a:{a}}}</style>
</head><body><div class="w">
{body}
<footer>{esc(C['brand'])} · 접수 {esc(C['phone'])}<br>매일 {esc(C['order_deadline'])}까지 접수 시 {esc(C['delivery_window'])} 배송</footer>
</div></body></html>"""

def cta():
    tel = C['phone'].replace('-', '')
    shop = C.get('shop_url')
    b = f"<a class='cta' href='tel:{tel}'>전화 주문 {esc(C['phone'])}</a>"
    if shop:
        b += (f"<a class='cta' style='background:#fff;color:var(--a);"
              f"border:2px solid var(--a)' href='{esc(shop)}' rel='nofollow'>"
              f"온라인 주문하기</a>")
    return b

def products():
    def row(p):
        thumb = (f"<img class='p-thumb' src='{esc(p['img'])}' alt='{esc(p['name'])}' "
                 f"width='56' height='56' loading='lazy'>" if p.get("img") else "")
        return (f"<tr><td style='display:flex;gap:10px;align-items:center'>{thumb}"
                f"<span>{esc(p['name'])}<br><span style='font-size:13px;color:var(--ink2)'>"
                f"{esc(p['note'])}</span></span></td><td class='p'>{esc(p['price'])}</td></tr>")
    r = "".join(row(p) for p in C["products"])
    return f"<h2>{esc(KW)} 가격</h2><table><tr><th>상품</th><th style='text-align:right'>가격</th></tr>{r}</table>"

def process(name):
    fmt = dict(name=name, brand=C['brand'], phone=C['phone'],
               deadline=C['order_deadline'], window=C['delivery_window'])
    return "<h2>주문부터 배송까지</h2><ol class='pr'>" + "".join(
        f"<li><b>{esc(t)}</b> — {esc(d.format(**fmt))}</li>" for t, d in C["process"]) + "</ol>"

def ribbon(name):
    groups = C.get("ribbons")
    if not groups:
        return ""
    intro = pick("ribbon_intro", name, "ribbon") or (
        "리본은 왼쪽에 보내는 분 정보, 오른쪽에 애도의 뜻을 담은 문구를 적습니다. "
        "종교를 모르실 때는 공통 문구를 사용하시면 무난합니다.")
    body = "".join(
        f"<h3>{esc(g)}</h3><ul class='rb'>" + "".join(f"<li>{esc(l)}</li>" for l in lines) + "</ul>"
        for g, lines in groups)
    return (f"<h2>리본 문구 — 종교별</h2>"
            f"<p class='lede' style='margin-bottom:8px'>{esc(intro)}</p>{body}")

def facility_intro(r):
    name, sgg, typ = r["name"], r["sigungu"], r.get("type", "")
    tmpl = pick("facility_open", name, "open") or "{name}은 {sgg} 지역 {fn}입니다."
    s = esc(tmpl.format(name=name, sgg=sgg, fn=FN))
    if typ:
        clause = pick("facility_type_clause", name, "type") or " {type} 형태로 운영됩니다."
        s += esc(clause.format(type=typ))
    if positive(r, "rooms") and positive(r, "coffins"):
        s += (f" 총 {esc(r['rooms'])}개의 빈소와 {esc(r['coffins'])}구의 안치 시설을 갖추고 있어 "
              f"동시에 여러 건의 조문을 진행할 수 있습니다.")
    if positive(r, "parking"):
        s += f" 주차는 약 {esc(r['parking'])}대까지 가능해 조문객이 몰리는 시간대에도 비교적 여유 있게 이용할 수 있습니다."
    if has(r, "extras"):
        s += f" 이 외에도 {esc(r['extras'])} 등의 부대시설을 함께 갖추고 있습니다."
    return f"<p>{s}</p>"

def buying_guide(name):
    text = pick("buying_guide", name, "buying_guide") or (
        "근조화환은 크기와 꽃의 구성에 따라 가격이 달라집니다. 개인 명의로 조용히 조의를 표할 때는 3단 일반형이 무난하고, "
        "거래처·단체 명의로 보낼 때는 고급형을, 임원·귀빈 등 각별한 예우가 필요한 자리에는 특대형 이상을 선택하시는 경우가 많습니다. "
        "장례식장 공간이 좁거나 화환 반입이 제한되는 경우에는 오브제나 바구니 형태로 대체할 수 있습니다. "
        "주문 시 화환 크기, 리본 문구, 보내는 분 성함만 알려주시면 나머지는 담당자가 확인해 안내해 드립니다.")
    return f"<h2>{esc(KW)} 고르는 법</h2><p>{esc(text)}</p>"

def etiquette(name):
    text = pick("etiquette", name, "etiquette") or (
        "장례식장 방문 시에는 상복이 아니어도 검은색 계열의 단정한 복장이 무난합니다. "
        "조문객은 상주보다 먼저 인사말을 건네지 않고, 짧은 목례 후 분향 또는 헌화를 마친 뒤 "
        "상주와 맞절하거나 악수로 위로의 뜻을 전합니다. "
        "부의금은 흰 봉투에 넣어 앞면에 부의(賻儀) 또는 근조(謹弔)라고 적고, "
        "뒷면 왼쪽 아래에 보내는 사람의 이름을 세로로 적는 것이 일반적입니다. "
        "화환은 부의금과 별도로 준비하는 것이 예의이며, 사정상 직접 조문이 어려운 경우에도 "
        "화환을 통해 애도의 뜻을 전할 수 있습니다.")
    return f"<h2>조문 예절과 부의금 안내</h2><p>{esc(text)}</p>"

def checklist(name):
    intro = pick("checklist_intro", name, "checklist") or "아래 정보를 미리 준비해 주시면 더 빠르고 정확하게 배송해 드릴 수 있습니다."
    return f"""<h2>{esc(KW)} 주문 전 확인 사항</h2>
<p>{esc(intro)}</p>
<ul class="rb">
<li>장례식장명과 빈소 호실 (모르시면 상주 성함으로 대체 가능)</li>
<li>리본에 넣을 문구와 보내는 분 성함 또는 단체명</li>
<li>배송 확인 연락을 받으실 휴대전화 번호</li>
<li>희망하시는 화환 종류와 예산</li>
</ul>"""

def dynamic_faqs(r):
    name = r["name"]
    out = []
    if positive(r, "rooms"):
        out.append((f"{name} 빈소는 몇 개인가요?",
                     f"총 {r['rooms']}개의 빈소를 운영하고 있습니다. 정확한 호실은 상주 성함으로 현장에서 확인해 드립니다."))
    if positive(r, "parking"):
        out.append((f"{name} 주차는 몇 대까지 가능한가요?",
                     f"약 {r['parking']}대까지 주차 가능한 것으로 확인됩니다. 조문객이 몰리는 시간대에는 여유 있게 방문하시길 권합니다."))
    elif has(r, "parking"):
        out.append((f"{name} 주차가 가능한가요?", "별도 주차 공간이 없는 시설입니다. 인근 공영주차장 이용을 권해 드립니다."))
    extras = r.get("extras", "")
    if "식당" in extras:
        out.append((f"{name} 조문객 식사가 가능한가요?", "네, 식당을 운영하고 있어 조문객 식사가 가능합니다."))
    if "유족대기실" in extras:
        out.append((f"{name}에 유족이 머무를 공간이 있나요?", "네, 별도의 유족대기실을 갖추고 있습니다."))
    if "매점" in extras:
        out.append((f"{name} 매점을 이용할 수 있나요?", "네, 매점이 있어 간단한 물품 구매가 가능합니다."))
    return out

def faqs(r):
    fmt = dict(deadline=C['order_deadline'], window=C['delivery_window'])
    common = [(q.format(**fmt), a.format(**fmt)) for q, a in C["faqs"]]
    items = (dynamic_faqs(r)[:3] + common)[:6]
    return f"<h2>{esc(r['name'])} {esc(KW)} 자주 묻는 질문</h2>" + "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in items)

def bugo_note():
    url = C.get("bugo_url")
    if not url:
        return ""
    return (f"<div class='note'><b>부고 소식은 이렇게 전하세요</b>"
            f"<p>아직 조문객들에게 부고를 알리는 문자나 카톡을 준비하지 못하셨다면 "
            f"<a href='{esc(url)}' rel='nofollow'>이지부고</a>의 무료 부고장 만들기를 이용해 보세요. "
            f"상주 성함, 빈소 위치, 발인 일정을 입력하면 모바일로 바로 공유할 수 있는 부고장이 만들어집니다.</p></div>")

def cremation_note(sido, cremation):
    if not cremation.get(sido):
        return ""
    slug = sido + "화장시설안내"
    return (f"<div class='note'><b>발인 이후 화장시설이 필요하신가요?</b>"
            f"<p>발인 이후 화장 절차를 준비 중이시라면, {esc(sido)} 화장시설의 주소·전화번호·화장로수 정보를 "
            f"확인해 보세요. <a href='/{enc(slug)}/'>{esc(sido)} 화장시설(화장장) 안내 보기 →</a></p></div>")

# ---------------- 시설 페이지 ----------------
def facility_page(r, siblings, cremation):
    name, sido, sgg = r["name"], r["sido"], r["sigungu"]
    slug = f"{name}{KW}"
    canon = f"https://{C['domain']}/{enc(slug)}/"
    kws = " · ".join([KW] + ALT[:2])
    title = f"{name} {KW} 주문 · {ALT[0] if ALT else KW} 배송 | {C['brand']}"
    desc = (f"{name} 빈소로 {ALT[0] if ALT else KW}을 배송합니다. "
            f"{C['products'][0]['price']}부터. {C['order_deadline']}까지 접수 시 {C['delivery_window']} 배송. "
            + (f"{r['address']}. " if has(r, 'address') else "") + f"{sgg} {FN} {KW} 주문.")

    # 05 시설 정보
    rows = []
    if has(r, "address"): rows.append(("주소", r["address"]))
    if has(r, "phone"):   rows.append(("전화", r["phone"] + " (시설 대표번호 · 주문 접수 아님)"))
    if has(r, "rooms"):   rows.append(("빈소", f"{r['rooms']}실"))
    if has(r, "coffins"): rows.append(("안치", f"{r['coffins']}구"))
    if has(r, "parking"): rows.append(("주차", f"{r['parking']}대"))
    if has(r, "extras"):  rows.append(("시설", r["extras"]))
    if has(r, "type"):    rows.append(("운영", r["type"]))
    info = "".join(f"<div><b>{esc(k)}</b><span>{esc(v)}</span></div>" for k, v in rows)
    info_block = f"<h2>{esc(name)} 안내</h2><div class='info'>{info}</div>" if rows else ""
    if has(r, "map"):
        info_block += f"<p><a href='{esc(r['map'])}' rel='nofollow'>지도에서 위치 보기 →</a></p>"

    lede = (f"{esc(name)} 빈소로 {esc(kws)}을 배송합니다. {esc(C['products'][0]['price'])}부터, "
            f"매일 {esc(C['order_deadline'])}까지 접수 시 {esc(C['delivery_window'])} 배송합니다."
            + (f" {esc(r['address'])}." if has(r, 'address') else ""))

    sgg_url = sgg_slug(sido, sgg)
    sib = "".join(f"<li><a href='/{enc(s+KW)}/'>{esc(s)} {esc(KW)}</a></li>" for s in siblings)
    body = f"""
<nav class="bc"><a href="/">홈</a> › <a href="/{enc(sido+FN)}/">{esc(sido)}</a> › <a href="/{enc(sgg_url)}/">{esc(sgg)}</a> › {esc(name)}</nav>
<h1>{esc(name)} {esc(KW)}</h1>
<p class="lede">{lede}</p>
{cta()}
{info_block}
{facility_intro(r)}
{products()}
{buying_guide(name)}
{checklist(name)}
{process(name)}
{ribbon(name)}
{etiquette(name)}
{faqs(r)}
{bugo_note()}
{cremation_note(sido, cremation)}
<h2>{esc(sgg)}의 다른 {esc(FN)}</h2>
<ul class="k">{sib}</ul>
<p style="margin-top:16px"><a href="/{enc(sgg_url)}/">{esc(sgg)} {esc(FN)} 전체 보기 →</a></p>
{cta()}
"""
    return slug, shell(title, desc, canon, body)

# ---------------- 허브 ----------------
def sigungu_page(sido, sgg, rows, other_sgg, cremation):
    slug = sgg_slug(sido, sgg)
    canon = f"https://{C['domain']}/{enc(slug)}/"
    title = f"{sgg} {FN} {KW} 주문 | {C['brand']}"
    desc = f"{sido} {sgg} {FN} {len(rows)}곳에 {ALT[0] if ALT else KW}을 배송합니다. {C['products'][0]['price']}부터."
    lst = "".join(f"<li><a href='/{enc(r['name']+KW)}/'>{esc(r['name'])} {esc(KW)}</a></li>" for r in rows)
    oth = "".join(f"<li><a href='/{enc(sgg_slug(sido, s))}/'>{esc(s)} {esc(FN)}</a></li>" for s in other_sgg)
    body = f"""
<nav class="bc"><a href="/">홈</a> › <a href="/{enc(sido+FN)}/">{esc(sido)}</a> › {esc(sgg)}</nav>
<h1>{esc(sgg)} {esc(FN)} {esc(KW)}</h1>
<p class="lede">{esc(sgg)} {esc(FN)} {len(rows)}곳에 {esc(KW)}을 배송합니다. {esc(C['products'][0]['price'])}부터.</p>
{cta()}
<h2>{esc(sgg)}의 {esc(FN)}</h2><ul class="k">{lst}</ul>
{products()}
{cremation_note(sido, cremation)}
<h2>{esc(sido)}의 다른 지역</h2><ul class="k">{oth}</ul>
"""
    return slug, shell(title, desc, canon, body)

def sido_page(sido, sgg_map, total, other_sido, cremation):
    slug = sido + FN
    canon = f"https://{C['domain']}/{enc(slug)}/"
    title = f"{sido} {FN} {KW} 주문 | {C['brand']}"
    desc = f"{sido} {FN} {total}곳에 {ALT[0] if ALT else KW}을 배송합니다. 매일 {C['order_deadline']}까지 접수."
    lst = "".join(f"<li><a href='/{enc(sgg_slug(sido, s))}/'>{esc(s)} <span style='color:#888'>{len(v)}</span></a></li>"
                  for s, v in sgg_map.items())
    oth = "".join(f"<li><a href='/{enc(s+FN)}/'>{esc(s)}</a></li>" for s in other_sido)
    body = f"""
<nav class="bc"><a href="/">홈</a> › {esc(sido)}</nav>
<h1>{esc(sido)} {esc(FN)} {esc(KW)}</h1>
<p class="lede">{esc(sido)} {esc(FN)} {total}곳에 {esc(KW)}을 배송합니다.</p>
{cta()}
<h2>시·군·구별 {esc(FN)}</h2><ul class="k">{lst}</ul>
{products()}
{cremation_note(sido, cremation)}
<h2>다른 지역</h2><ul class="k">{oth}</ul>
"""
    return slug, shell(title, desc, canon, body)

def cremation_hub_page(sido, rows):
    slug = sido + "화장시설안내"
    canon = f"https://{C['domain']}/{enc(slug)}/"
    title = f"{sido} 화장시설(화장장) 안내 | {C['brand']}"
    desc = f"{sido} 화장시설 {len(rows)}곳의 주소·전화번호·화장로수 안내."
    trows = "".join(
        f"<tr><td>{esc(r['name'])}<br><span style='font-size:13px;color:var(--ink2)'>{esc(r['address'])}</span></td>"
        f"<td style='white-space:nowrap'>{esc(r['phone'])}</td></tr>" for r in rows)
    body = f"""
<nav class="bc"><a href="/">홈</a> › {esc(sido)} 화장시설 안내</nav>
<h1>{esc(sido)} 화장시설(화장장) 안내</h1>
<p class="lede">발인 이후 화장 절차를 준비 중이시라면 {esc(sido)} 화장시설 {len(rows)}곳의 정보를 확인해 보세요.</p>
{cta()}
<h2>{esc(sido)} 화장시설 목록</h2>
<table><tr><th>시설명 · 주소</th><th>전화</th></tr>{trows}</table>
<p style="margin-top:16px"><a href="/{enc(sido+FN)}/">{esc(sido)} {esc(FN)} {esc(KW)} 보기 →</a></p>
"""
    return slug, shell(title, desc, canon, body)

def home(tree, total, cremation):
    canon = f"https://{C['domain']}/"
    title = f"전국 {FN} {KW} 주문 · {ALT[0] if ALT else KW} 배송 | {C['brand']}"
    desc = f"전국 {FN} {total}곳에 {ALT[0] if ALT else KW}을 배송합니다. {C['products'][0]['price']}부터."
    lst = "".join(f"<li><a href='/{enc(sd+FN)}/'>{esc(sd)} <span style='color:#888'>"
                  f"{sum(len(v) for v in m.values())}</span></a></li>" for sd, m in tree.items())
    body = f"""
<h1>전국 {esc(FN)} {esc(KW)}</h1>
<p class="lede">{esc(C['hero_line'])}</p>
{cta()}
<h2>지역별 {esc(FN)}</h2><ul class="k">{lst}</ul>
{products()}
{process('해당 ' + FN)}
{ribbon('전국')}
{faqs({'name': '전국 ' + FN, 'rooms': '', 'parking': '', 'extras': ''})}
"""
    return shell(title, desc, canon, body, extra_head=site_verification_tags())

# ---------------- 빌드 ----------------
def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", type=int, default=0)
    st = ap.parse_args().stage
    tree, rows = load()
    cremation = load_crematorium()
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    urls = []
    total = len(rows)

    sgg_sido = {}
    for sd, m in tree.items():
        for sg in m:
            sgg_sido.setdefault(sg, set()).add(sd)
    for sd, m in tree.items():
        for sg in m:
            SGG_SLUG[(sd, sg)] = (sd + sg + FN) if len(sgg_sido[sg]) > 1 else (sg + FN)

    write(os.path.join(OUT, "index.html"), home(tree, total, cremation))
    urls.append(("", "1.0", "daily"))

    sidos = list(tree)
    for sd in sidos:
        m = tree[sd]
        others = [x for x in sidos if x != sd]
        slug, page = sido_page(sd, m, sum(len(v) for v in m.values()), others, cremation)
        write(os.path.join(OUT, slug, "index.html"), page); urls.append((slug, "0.9", "weekly"))
        sggs = list(m)
        for sg in sggs:
            rs = m[sg]
            if sg != sd:  # 세종처럼 시군구=시도 자신이면 시도 허브와 슬러그가 겹쳐 별도 페이지 생략
                slug, page = sigungu_page(sd, sg, rs, [x for x in sggs if x != sg][:12], cremation)
                write(os.path.join(OUT, slug, "index.html"), page); urls.append((slug, "0.8", "weekly"))
            pick = rs if st == 0 else rs[:max(1, int(len(rs) * (0.3 if st == 1 else 0.7)))]
            for r in pick:
                sib = [x["name"] for x in rs if x["name"] != r["name"]][:12]
                slug, page = facility_page(r, sib, cremation)
                write(os.path.join(OUT, slug, "index.html"), page); urls.append((slug, "0.7", "weekly"))

    for sd, rs in cremation.items():
        slug, page = cremation_hub_page(sd, rs)
        write(os.path.join(OUT, slug, "index.html"), page); urls.append((slug, "0.6", "monthly"))

    assets_dir = os.path.join(ROOT, "assets")
    if os.path.isdir(assets_dir):
        shutil.copytree(assets_dir, os.path.join(OUT, "assets"))

    base = f"https://{C['domain']}"
    lastmod = date.today().isoformat()
    write(os.path.join(OUT, "sitemap.xml"),
          '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{base}/{enc(s)}{'/' if s else ''}</loc><lastmod>{lastmod}</lastmod>"
                    f"<changefreq>{cf}</changefreq><priority>{pr}</priority></url>\n"
                    for s, pr, cf in urls) + "</urlset>\n")
    write(os.path.join(OUT, "robots.txt"), f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")

    key = C.get("indexnow_key")
    if key:
        write(os.path.join(OUT, f"{key}.txt"), key)  # 재빌드해도 안 사라지게 config 값으로 매번 재생성

    print(f"시설 {total}곳 + 화장시설 {len(cremation)}개 시도 → {len(urls)}개 URL 생성  ({OUT})")

if __name__ == "__main__":
    main()
