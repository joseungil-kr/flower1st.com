#!/usr/bin/env python3
"""
지역별 근조화환 추가배송비 안내 페이지 생성기
- delivery_fees.json 및 facilities.csv 기반
- 전국 192개 도서산간/원거리 읍·면·동 및 시·군 배송비 안내 페이지 일괄 생성
- 해당 지역 소재 장례식장 및 관내 인근 장례식장 상호 연결 링크 탑재
- 화환 상품/가격, 배송 절차, 주문 유의사항, FAQ, Schema.org 구조화 데이터 내장
"""
import os, sys, json, csv, urllib.parse, html

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
C = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
FEES_PATH = os.path.join(ROOT, "delivery_fees.json")
FEES = json.load(open(FEES_PATH, encoding="utf-8")) if os.path.isfile(FEES_PATH) else []
FACILITIES = [r for r in csv.DictReader(open(os.path.join(ROOT, "facilities.csv"), encoding="utf-8"))
              if (r.get("name") or "").strip()]

FN, KW = C["facility_noun"], C["primary_kw"]

# SGG_SLUG mapping
SGG_SLUG = {}
sgg_sido_map = {}
for r in FACILITIES:
    sgg_sido_map.setdefault(r["sigungu"], set()).add(r["sido"])
for r in FACILITIES:
    sd, sg = r["sido"], r["sigungu"]
    SGG_SLUG[(sd, sg)] = (sd + sg + FN) if len(sgg_sido_map[sg]) > 1 else (sg + FN)

def sgg_url_slug(sido, sgg):
    if (sido, sgg) in SGG_SLUG:
        return SGG_SLUG[(sido, sgg)]
    return sido + FN # fallback to sido hub if sigungu not in facilities DB (e.g. 계룡시)

def esc(s): return html.escape(str(s or ""), quote=True)
def enc(p): return urllib.parse.quote(p, safe="/")

def get_fee_slug(entry):
    sgg = entry["sigungu"]
    emd = entry.get("emd", "")
    if emd:
        return f"{sgg} {emd} 근조화환 배송비"
    return f"{sgg} 근조화환 배송비"

def get_fee_display(entry):
    sgg = entry["sigungu"]
    emd = entry.get("emd", "")
    if emd:
        return f"{sgg} {emd}"
    return sgg

def find_facilities_for_entry(entry):
    sido = entry["sido"]
    sgg = entry["sigungu"]
    emd = entry.get("emd", "")
    
    direct_facs = []
    nearby_facs = []
    
    for f in FACILITIES:
        # Check sido
        if f["sido"] != sido and not (sido == "전라남도" and f["sido"] in ["전라남도", "광주광역시"]):
            continue
        
        sgg_clean = sgg.split()[0]
        if sgg_clean in f["sigungu"] or sgg in f["sigungu"]:
            if emd and (emd in f["address"] or emd in f["name"]):
                direct_facs.append(f)
            else:
                nearby_facs.append(f)
                
    return direct_facs, nearby_facs

def cta():
    tel = C["phone"].replace("-", "")
    shop = C.get("shop_url")
    b = f"<a class='cta' href='tel:{tel}'>전화 주문 및 배송비 상담 {esc(C['phone'])}</a>"
    if shop:
        b += (f"<a class='cta' style='background:#fff;color:var(--a);"
              f"border:2px solid var(--a)' href='{esc(shop)}' rel='nofollow'>"
              f"온라인 바로 주문하기</a>")
    return b

def products_section(fee_amount):
    def row(p):
        thumb = (f"<img class='p-thumb' src='{esc(p['img'])}' alt='{esc(p['name'])}' "
                 f"width='56' height='56' loading='lazy'>" if p.get("img") else "")
        return (f"<tr><td style='display:flex;gap:10px;align-items:center'>{thumb}"
                f"<span>{esc(p['name'])}<br><span style='font-size:13px;color:var(--ink2)'>"
                f"{esc(p['note'])}</span></span></td><td class='p'>{esc(p['price'])}</td></tr>")
    r = "".join(row(p) for p in C["products"])
    return (f"<h2>{esc(KW)} 가격 안내 (기본 화환 정찰가)</h2>"
            f"<p class='lede'>기본 화환 상품 가격에 지역별 공식 거리 추가배송비(<b>{esc(fee_amount)}</b>)가 추가 적용됩니다.</p>"
            f"<table><tr><th>상품명</th><th style='text-align:right'>기본 가격</th></tr>{r}</table>")

def build_fee_page(entry):
    sido = entry["sido"]
    sgg = entry["sigungu"]
    emd = entry.get("emd", "")
    fee = entry["fee"]
    
    slug = get_fee_slug(entry)
    disp = get_fee_display(entry)
    canon = f"https://{C['domain']}/{enc(slug)}/"
    
    title = f"{disp} 근조화환 추가배송비 안내 · {disp} 장례식장 화환 배송 | {C['brand']}"
    desc = f"{sido} {disp} 지역 근조화환 배송 시 원거리·외곽 추가배송비 안내 ({fee}). {disp} 소재 및 인근 장례식장 목록, 당일 특급 배송, 현장 안착 사진 안심 전송 서비스."
    
    direct_facs, nearby_facs = find_facilities_for_entry(entry)
    
    # Breadcrumbs & Hub URLs
    sgg_url = sgg_url_slug(sido, sgg)
    sido_url = sido + FN
    
    # Direct facilities section
    if direct_facs:
        direct_items = "".join(
            f"<li><a href='/{enc(f['name']+KW)}/'><b>{esc(f['name'])}</b>"
            f"<br><span style='font-size:13px;color:var(--ink2)'>{esc(f['address'])}</span></a></li>"
            for f in direct_facs
        )
        direct_section = (f"<h2>{esc(disp)} 소재 장례식장 안내 ({len(direct_facs)}곳)</h2>"
                          f"<p class='lede'>{esc(disp)} 관내에 위치한 장례식장으로, 원거리 추가배송비 <b>{esc(fee)}</b>가 적용되어 안전하고 정확하게 배송됩니다.</p>"
                          f"<ul class='k'>{direct_items}</ul>")
    else:
        direct_section = (f"<h2>{esc(disp)} 장례식장 배송 안내</h2>"
                          f"<div class='note'><b>{esc(disp)} 관내 장례 및 가정/야외 배송</b>"
                          f"<p>{esc(disp)} 관내 장례식장 또는 자택, 종교시설, 마을회관 등의 분향소로 배송 시 "
                          f"원거리·도서산간 추가배송비(<b>{esc(fee)}</b>)가 적용됩니다. 인근 시·군 거점 화원에서 당일 3시간 내 신속 제작되어 도착합니다.</p></div>")

    # Nearby facilities in the parent sigungu
    if nearby_facs:
        nearby_items = "".join(
            f"<li><a href='/{enc(f['name']+KW)}/'>{esc(f['name'])} {esc(KW)}</a></li>"
            for f in nearby_facs[:12]
        )
        nearby_section = (f"<h2>{esc(sgg)} 관내 다른 주요 장례식장</h2>"
                          f"<p class='lede'>{esc(sgg)} 중심가 및 인근 장례식장으로도 상시 빠른 배송이 가능합니다.</p>"
                          f"<ul class='k'>{nearby_items}</ul>"
                          f"<p style='margin-top:14px'><a href='/{enc(sgg_url)}/'>{esc(sgg)} 장례식장 전체보기 →</a></p>")
    else:
        nearby_section = f"<p style='margin-top:14px'><a href='/{enc(sido_url)}/'>{esc(sido)} 장례식장 전체보기 →</a></p>"

    # Fee details notice
    notice_section = f"""<h2>{esc(disp)} 근조화환 배송비 및 배송 시스템 안내</h2>
<div class='note'>
<b>1. 추가배송비 {esc(fee)} 적용 기준</b>
<p>{esc(sido)} {esc(disp)} 지역은 시·군 중심 제휴 화원과의 거리 및 지형적 특성(도서·산간·원거리 외곽)으로 인해 <b>{esc(fee)}</b>의 공식 추가배송비가 부과됩니다. 사전 공지된 투명한 정찰제로 운영되며 현장에서 기사에게 별도 요금을 요구하지 않습니다.</p>
</div>
<div class='note'>
<b>2. 당일 특급 배송 및 생화 품질 보증</b>
<p>이동 거리가 있더라도 사전 입고된 싱싱하고 단단한 특상급 백색 국화만을 엄선하여 제작합니다. 이동 중 흔들림이나 꽃잎 상함이 없도록 고정식 특장 차량으로 안전하게 운송됩니다.</p>
</div>
<div class='note'>
<b>3. 현장 안착 사진 및 리본 문구 실시간 전송</b>
<p>{esc(disp)} 장례식장 또는 빈소 앞 안착 즉시, 리본 문구와 화환 전체가 선명하게 촬영된 확인 사진을 주문 고객님의 휴대전화 번호로 문자로 즉시 발송해 드립니다.</p>
</div>"""

    # FAQ
    faqs = [
        (f"{disp} 지역으로 근조화환 주문 시 추가배송비는 얼마인가요?",
         f"{sido} {disp} 지역은 관내 외곽·도서산간 지역으로 분류되어 기본 화환 가격 외에 추가배송비 {fee}이 정찰 적용됩니다. 주문 시 함께 결제되며 현장 추가 비용은 일체 없습니다."),
        (f"{disp}까지 당일 배송 소요 시간은 얼마나 걸리나요?",
         f"주문 접수 즉시 {sido} 관내 최인접 거점 화원에서 제작에 들어가며, 이동 거리를 감안하여 평균 3시간~4시간 이내에 현장 빈소까지 안전하게 안착 배송됩니다."),
        (f"{disp} 장례식장 빈소 호실을 모르는데 주문이 가능한가요?",
         f"네, 고인 또는 상주 성함만 알려주시면 배송 기사님이 {disp} 현장 안내실에서 빈소 호실을 직접 확인한 후 제자리에 단정히 배치해 드립니다."),
        ("배송 완료 후 설치 사진을 받아볼 수 있나요?",
         f"네, {disp} 빈소 앞 설치가 완료되는 즉시 리본 문구와 화환 실물이 선명하게 나오는 사진을 주문자님의 휴대전화로 전송해 드립니다.")
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)

    # Breadcrumbs HTML
    bc_html = f"""<nav class="bc"><a href="/">홈</a> › <a href="/{enc(sido_url)}/">{esc(sido)}</a> › <a href="/{enc(sgg_url)}/">{esc(sgg)}</a> › {esc(disp)} 배송비</nav>"""

    body = f"""
{bc_html}
<h1>{esc(disp)} 근조화환 추가배송비 안내</h1>
<p class="lede">{esc(sido)} {esc(disp)} 지역은 도서·산간·외곽 배송 구역으로 추가배송비 <b>{esc(fee)}</b>가 적용됩니다. 3시간 이내 당일 배송 및 현장 안착 사진 전송.</p>
{cta()}
{direct_section}
{products_section(fee)}
{notice_section}
<h2>{esc(disp)} 배송 관련 자주 묻는 질문</h2>
{faq_html}
{nearby_section}
{cta()}
"""

    # Schema.org JSON-LD
    schema_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Florist",
                "name": f"{disp} 근조화환 배송 - {C['brand']}",
                "url": canon,
                "telephone": C["phone"],
                "priceRange": f"{C['products'][0]['price']} ~ {C['products'][-1]['price']} (+배송비 {fee})",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": sgg,
                    "addressRegion": sido,
                    "addressCountry": "KR"
                }
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": f"https://{C['domain']}/"},
                    {"@type": "ListItem", "position": 2, "name": sido, "item": f"https://{C['domain']}/{enc(sido_url)}/"},
                    {"@type": "ListItem", "position": 3, "name": sgg, "item": f"https://{C['domain']}/{enc(sgg_url)}/"},
                    {"@type": "ListItem", "position": 4, "name": f"{disp} 배송비 안내", "item": canon}
                ]
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}
                    } for q, a in faqs
                ]
            }
        ]
    }
    schema_json = json.dumps(schema_data, ensure_ascii=False)
    extra_head = f'<script type="application/ld+json">{schema_json}</script>'

    a = C["accent"]
    page_html = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="{esc(C['brand'])}">
<meta property="og:image" content="https://{C['domain']}/assets/og.jpg">
<link rel="icon" href="/assets/favicon.png" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
{extra_head}
<meta name="theme-color" content="{a}">
<link rel="stylesheet" href="/assets/style.css">
<style>:root{{--a:{a}}}</style>
</head><body><div class="w">
{body}
<footer>{esc(C['brand'])} · 접수 {esc(C['phone'])}<br>매일 {esc(C['order_deadline'])}까지 접수 시 3시간 이내 당일 배송</footer>
</div></body></html>"""

    return slug, page_html

def main():
    print(f"총 {len(FEES)}개 지역별 추가배송비 안내 페이지 빌드 시작...")
    built = 0
    for e in FEES:
        slug, html_content = build_fee_page(e)
        out_path = os.path.join(OUT, slug, "index.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        built += 1
    print(f"추가배송비 {built}개 페이지 생성 완료! (out/ 디렉토리)")

if __name__ == "__main__":
    main()
