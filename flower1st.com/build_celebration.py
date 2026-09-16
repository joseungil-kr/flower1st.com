#!/usr/bin/env python3
"""
전국 시 단위 개업식 축하화환 페이지 생성기
- celebration_cities.json 기반
- 안산시, 수원시 등 83개 시 단위 축하화환 페이지 일괄 생성
- 화환종류 및 가격, 주문방법, 주문 시 유의사항, 배달 가능 동/시장/먹자골목 롱테일 섹션 탑재
- Schema.org (LocalBusiness, BreadcrumbList, FAQPage) 구조화 데이터 내장
"""
import json, os, urllib.parse, html

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
C = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
CITIES_PATH = os.path.join(ROOT, "celebration_cities.json")
CITIES = json.load(open(CITIES_PATH, encoding="utf-8")) if os.path.isfile(CITIES_PATH) else []

def esc(s): return html.escape(str(s or ""), quote=True)
def enc(p): return urllib.parse.quote(p, safe="/")

# 축하화환 전용 상품군
CELEB_PRODUCTS = [
    {"name": "축하 3단 일반형", "price": "59,000원", "note": "개업식·이전·창립기념 기본형 조화 (실속 추천)", "img": "/assets/product/f1.jpg"},
    {"name": "축하 3단 고급형", "price": "79,000원", "note": "풍성한 계절꽃과 거베라 포인트 (기업·단체 1위)", "img": "/assets/product/f2.jpg"},
    {"name": "축하 3단 특대형", "price": "109,000원", "note": "행사장을 빛내는 웅장하고 풍성한 VIP 화환", "img": "/assets/product/f3.jpg"},
    {"name": "축하 4단 프리미엄", "price": "149,000원", "note": "최고의 축하와 성공을 기원하는 대형 매장 전용", "img": "/assets/product/f4.jpg"},
    {"name": "개업 축하 대박 화분 (금전수·스투키)", "price": "89,000원", "note": "실내 매장에 오래 두고 보는 공기정화 식물 화분"}
]

# 축하 리본 문구 모음
CELEB_RIBBONS = [
    ("대표적인 기본 축하 문구", [
        "祝 開業 (축 개업) — 개업을 축하합니다",
        "祝 發展 (축 발전) — 무궁한 발전을 기원합니다",
        "祝 開院 (축 개원) / 祝 開館 (축 개관)",
        "祝 移轉 (축 이전) — 새로운 시작과 번창을 응원합니다"
    ]),
    ("센스 있는 대박 기원 문구 (인기)", [
        "돈세다 잠드소서",
        "대박나서 건물사자!",
        "들숨에 손님, 날숨에 매출!",
        "사장님 될 줄 알았으면 더 잘할걸",
        "만수르가 돈 빌리러 오는 그날까지!"
    ]),
    ("격식 있는 비즈니스·기업 축하 문구", [
        "새로운 도약과 무궁한 번창을 진심으로 축하드립니다",
        "귀사의 번영과 건승을 기원합니다",
        "뜻깊은 개업을 맞이하여 앞날에 큰 영광이 함께하길 기원합니다"
    ])
]

def cta():
    tel = C["phone"].replace("-", "")
    shop = C.get("shop_url")
    b = f"<a class='cta' href='tel:{tel}'>전화 주문 {esc(C['phone'])}</a>"
    if shop:
        b += (f"<a class='cta' style='background:#fff;color:var(--a);"
              f"border:2px solid var(--a)' href='{esc(shop)}' rel='nofollow'>"
              f"온라인 간편 주문하기</a>")
    return b

def products_section(city_name):
    rows = []
    for p in CELEB_PRODUCTS:
        thumb = f"<img class='p-thumb' src='{esc(p['img'])}' alt='{esc(p['name'])}' width='56' height='56' loading='lazy'>" if p.get("img") else ""
        rows.append(
            f"<tr><td style='display:flex;gap:10px;align-items:center'>{thumb}"
            f"<span>{esc(p['name'])}<br><span style='font-size:13px;color:var(--ink2)'>"
            f"{esc(p['note'])}</span></span></td><td class='p'>{esc(p['price'])}</td></tr>"
        )
    return f"<h2>{esc(city_name)} 축하화환 가격 및 상품 안내</h2><table><tr><th>상품명</th><th style='text-align:right'>정찰 가격</th></tr>{''.join(rows)}</table>"

def process_section(city_name):
    return f"""<h2>{esc(city_name)}꽃집 화환 주문방법 (4단계 안내)</h2>
<p>{esc(city_name)} 관내 제휴 화원 네트워크를 통해 주문 즉시 신선한 생화로 제작되며, 개업 행사 전 최적의 타이밍에 안착됩니다.</p>
<ol class='pr'>
<li><b>주문 접수 및 상담</b> — 개업식 매장 상호명, 주소, 개업 행사 일시 및 리본 축하 문구를 확인합니다.</li>
<li><b>화환 맞춤 제작</b> — 당일 입고된 신선한 생화와 특상급 거베라를 선별하여 전문 플로리스트가 꼼꼼히 제작합니다.</li>
<li><b>개업 현장 특급 배송</b> — 행사가 시작되기 1~2시간 전 매장에 안전하게 도착하여 가장 돋보이는 자리에 배치합니다.</li>
<li><b>현장 안착 사진 전송</b> — 배송 완료 직후 화환 실물과 리본 문구가 선명하게 보이는 확인 사진을 주문 고객님께 문자로 전송해 드립니다.</li>
</ol>"""

def notice_section(city_name):
    return f"""<h2>개업식 화환 주문 시 핵심 유의사항</h2>
<div class='note'>
<b>1. 행사 시작 1~2시간 전 배송을 권장합니다</b>
<p>개업 당일에는 손님맞이와 매장 준비로 매우 혼잡합니다. 행사가 시작되기 전 미리 화환이 안착되어야 매장 입구가 화사하게 정돈되고 축하 분위기가 살아납니다.</p>
</div>
<div class='note'>
<b>2. 매장 환경에 어울리는 화환 형태 선택</b>
<p>야외 인도나 매장 입구가 넓은 로드샵, 식당, 카페의 경우 3단 축하화환이 가장 돋보입니다. 반면 백화점 입점 매장, 지하상가, 오피스텔 등 화환 배치가 협소한 곳은 '개업 축하 화분(금전수/스투키)' 또는 '스탠드 오브제'를 추천해 드립니다.</p>
</div>
<div class='note'>
<b>3. 정확한 리본 문구(보내는 분 직함/상호) 확인</b>
<p>축하 문구(오른쪽)와 보내는 분 성함/회사명/직함(왼쪽)이 오타 없이 정확해야 품격이 전달됩니다. 전화 주문 시 전문 상담원이 문구를 재확인해 드립니다.</p>
</div>"""

def ribbons_section():
    blocks = []
    for cat, items in CELEB_RIBBONS:
        li = "".join(f"<li>{esc(x)}</li>" for x in items)
        blocks.append(f"<h3>{esc(cat)}</h3><ul class='rb'>{li}</ul>")
    return "<h2>개업식 인기 축하 리본 문구 모음</h2><p class='lede'>리본 좌측에는 보내는 분의 회사명·직함·성함을, 우측에는 축하 문구를 인쇄합니다.</p>" + "".join(blocks)

def local_longtail_section(city_info):
    city = city_info["city"]
    short = city_info["short_name"]
    dongs = city_info.get("dongs", [])
    markets = city_info.get("markets", [])
    commercial = city_info.get("commercial_areas", [])

    dong_tags = " ".join(f"<span style='display:inline-block;background:var(--soft);border:1px solid var(--line);border-radius:4px;padding:3px 8px;margin:3px 2px;font-size:13px'>{esc(d)}</span>" for d in dongs)
    market_list = ", ".join(esc(m) for m in markets) if markets else f"{city} 내 주요 전통시장 및 상가"
    comm_list = ", ".join(esc(c) for c in commercial) if commercial else f"{city} 전역 로데오거리 및 상업지구"

    return f"""<h2>{esc(city)} 전지역 당일 화환 배달 가능 구역 안내</h2>
<p class='lede'>{esc(city)} 시내 모든 동과 읍·면 지역은 물론, 주요 번화가 상권과 전통시장까지 빠짐없이 직배송합니다.</p>

<div class='info'>
<div><b>배달 가능 행정구역</b><div style='line-height:1.9'>{dong_tags}</div></div>
</div>

<h3>{esc(city)} 주요 상권 및 먹자골목 배달</h3>
<p>{esc(comm_list)} 등 유동인구가 많은 대표 번화가 및 골목 상권의 신규 오픈 매장, 카페, 음식점, 학원, 병의원 개업식까지 신속하게 찾아갑니다.</p>

<h3>{esc(city)} 전통시장 및 상점가 배달</h3>
<p>{esc(market_list)} 등 시장 내 상점 개업식이나 점포 이전 축하 화환도 정확한 점포명과 위치를 확인하여 안전하게 설치해 드립니다.</p>"""

def nearby_cities_section(current_slug):
    links = []
    for c in CITIES:
        if c["slug"] != current_slug:
            links.append(f"<li><a href='/{enc(c['slug'])}/'>{esc(c['city'])} 축하화환</a></li>")
    return f"<h2>전국 주요 도시 축하화환 바로가기</h2><ul class='k'>{''.join(links[:18])}</ul>"

def celebration_faqs(city_name):
    items = [
        (f"{city_name} 지역 당일 주문 시 몇 시간 만에 배송되나요?",
         f"{city_name} 관내 제휴 화원에서 주문 접수 즉시 제작하여 평균 2~3시간 이내에 개업 매장 앞까지 신속하게 안착 배송됩니다. 개업 행사 시각이 지정되어 있을 경우 예약 배송도 가능합니다."),
        ("매장 층수나 정확한 번지를 몰라도 상호명만으로 배송이 가능한가요?",
         f"네, {city_name} 관내 상호명과 대략적인 위치(예: OO동 OO역 인근)만 알려주시면 배송 기사님이 현장에서 위치를 정확히 확인한 후 배치해 드립니다."),
        ("화환 배송이 끝나면 사진을 문자로 받아볼 수 있나요?",
         "네, 개업식 현장에 화환이 반입·설치되면 리본 문구와 화환 전체가 선명하게 보이는 확인 사진을 주문자님의 휴대전화 번호로 즉시 전송해 드립니다."),
        ("개업 화환 리본 문구는 어떤 것을 주로 쓰나요?",
         "가장 보편적인 '祝 開業 (축 개업)'이나 '祝 發展 (축 발전)'부터, 지인 간에 인기 있는 '돈세다 잠드소서', '대박나서 건물사자' 등 원하시는 문구를 무료로 고급 리본에 출력해 드립니다.")
    ]
    details = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in items)
    return f"<h2>{esc(city_name)} 축하화환 자주 묻는 질문</h2>{details}", items

def build_celebration_page(city_info):
    city = city_info["city"]
    sido = city_info["sido"]
    slug = city_info["slug"]
    short = city_info["short_name"]
    canon = f"https://{C['domain']}/{enc(slug)}/"

    title = f"{city} 축하화환 주문 · {short}꽃집 개업화환 당일 배달 | {C['brand']}"
    desc = f"{city} 전지역 개업식·이전 축하화환 59,000원부터. {city} 꽃집 관내 3시간 특급 배송, 설치 사진 문자 전송, 리본 무료 제작."

    faq_html, faq_items = celebration_faqs(city)

    body = f"""
<nav class="bc"><a href="/">홈</a> › <a href="/{enc(sido+'장례식장')}/">{esc(sido)}</a> › {esc(city)} 축하화환</nav>
<h1>{esc(city)} 축하화환 · {esc(short)}꽃집 개업식 화환 배달</h1>
<p class="lede">{esc(city)} 전지역 개업식·개원식·이전·창립기념 축하화환을 당일 3시간 이내에 정성껏 배송합니다. 59,000원 정찰제, 현장 안착 사진 안심 전송.</p>
{cta()}
{products_section(city)}
{process_section(city)}
{notice_section(city)}
{ribbons_section()}
{local_longtail_section(city_info)}
{faq_html}
{nearby_cities_section(slug)}
<p style="margin-top:20px"><a href="/">전국 장례식장 근조화환 전체보기 →</a></p>
{cta()}
"""

    faq_entities = [
        {
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a}
        } for q, a in faq_items
    ]

    schema_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Florist",
                "name": f"{city} 축하화환 배달 - {C['brand']}",
                "url": canon,
                "telephone": C["phone"],
                "priceRange": "59,000원 ~ 149,000원",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": city,
                    "addressRegion": sido,
                    "addressCountry": "KR"
                }
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": f"https://{C['domain']}/"},
                    {"@type": "ListItem", "position": 2, "name": sido, "item": f"https://{C['domain']}/{enc(sido+'장례식장')}/"},
                    {"@type": "ListItem", "position": 3, "name": f"{city} 축하화환", "item": canon}
                ]
            },
            {
                "@type": "FAQPage",
                "mainEntity": faq_entities
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
    print(f"총 {len(CITIES)}개 시 단위 축하화환 페이지 빌드 시작...")
    built = 0
    for c in CITIES:
        slug, html_content = build_celebration_page(c)
        out_path = os.path.join(OUT, slug, "index.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        built += 1
    print(f"축하화환 {built}개 페이지 생성 완료! (out/ 디렉토리)")

if __name__ == "__main__":
    main()
