#!/usr/bin/env python3
"""
전국장사시설_정리.xlsx (장례식장 시트) -> facilities.csv
화장시설·자연장지·봉안시설·묘지현황 시트 -> facilities_기타.csv (원본 그대로, 2차 보관)

python convert_xlsx.py
"""
import openpyxl, csv, re, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(ROOT, "..", "자료", "전국장사시설_정리.xlsx")

INSTALLED = {"식당", "매점", "주차장", "유족대기실", "장애인편의시설"}

BRANCH_HINT = re.compile(r"(점|지점|센터점|타워|호관|본관|별관)$")
CORP_WORDS = re.compile(r"주식회사|유한회사|사단법인|재단법인|㈜")
ALLOWED = re.compile(r"[^가-힣a-zA-Z0-9 ]")


def clean_num(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s == "" or s.lower() == "null":
        return ""
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return s


def clean_str(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() == "null" else s


def normalize_name(raw):
    """returns (name, change_note or None)"""
    s = re.sub(r"\s+", " ", raw.strip())

    def paren_repl(m):
        inner = m.group(1).strip()
        if BRANCH_HINT.search(inner):
            return " " + inner  # 지점 구분 -> 괄호 떼고 이어 표기
        return " "  # 법인표기·구칭·별칭 등은 전부 삭제(단어 붙지 않게 공백으로)

    s = re.sub(r"\(([^()]*)\)", paren_repl, s)
    s = CORP_WORDS.sub(" ", s)      # 괄호 밖 법인표기(주식회사 등)
    s = ALLOWED.sub("", s)         # 슬러그에 못 쓰는 특수문자
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("장례예식장", "장례식장")  # "예식장"도 장례식장 의미 -> 표기 통일

    if "장례식장" not in s:
        s = s + "장례식장"

    note = f"{raw}  ->  {s}" if s != raw else None
    return s, note


def main():
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

    # ---- 장례식장 -> facilities.csv ----
    ws = wb["장례식장"]
    rows_iter = ws.iter_rows(min_row=1, values_only=True)
    header = next(rows_iter)
    idx = {h: i for i, h in enumerate(header)}

    out_rows = []
    change_notes = []
    seen_exact = {}  # (name, address) -> True, dup filtering
    name_addr = defaultdict(list)  # normalized name -> [(sigungu, address, row)]

    raw_rows = list(rows_iter)
    for r in raw_rows:
        name_raw = clean_str(r[idx["시설명"]])
        if not name_raw:
            continue
        sido = clean_str(r[idx["시도"]])
        sigungu = clean_str(r[idx["시군구"]])
        address = clean_str(r[idx["주소"]])
        phone = clean_str(r[idx["전화번호"]])
        rooms = clean_num(r[idx["빈소수"]])
        coffins = clean_num(r[idx["안치가능구수"]])
        parking = clean_num(r[idx["주차대수"]])
        gongsa = clean_str(r[idx["공설/사설"]])
        optype = clean_str(r[idx["운영종류"]])
        ftype = f"{gongsa}({optype})" if gongsa and optype else gongsa

        extras = "·".join(
            f for f in ["식당", "매점", "주차장", "유족대기실", "장애인편의시설"]
            if clean_str(r[idx[f]]) == "설치"
        )

        name, note = normalize_name(name_raw)
        if note:
            change_notes.append(note)

        key = (name, address)
        if key in seen_exact:
            continue  # 완전 동일(동일명+동일주소) 중복 -> 스킵
        seen_exact[key] = True

        row = {
            "sido": sido, "sigungu": sigungu, "name": name, "address": address,
            "phone": phone, "rooms": rooms, "coffins": coffins, "parking": parking,
            "extras": extras, "type": ftype, "map": "",
        }
        out_rows.append(row)
        name_addr[name].append(address)

    # 동명이지역 처리: name 중복 & 주소 다름 -> 시군구+명칭으로 변경
    dup_report = []
    name_count = defaultdict(int)
    for row in out_rows:
        name_count[row["name"]] += 1
    for row in out_rows:
        if name_count[row["name"]] > 1:
            old = row["name"]
            row["name"] = row["sigungu"] + row["name"]
            dup_report.append(f"{old} ({row['sido']} {row['sigungu']}) -> {row['name']}")

    with open(os.path.join(ROOT, "facilities.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sido", "sigungu", "name", "address", "phone",
                                           "rooms", "coffins", "parking", "extras", "type", "map"])
        w.writeheader()
        w.writerows(out_rows)

    # ---- 나머지 시트 -> facilities_기타.csv (원본 그대로, 2차 보관) ----
    other_sheets = ["화장시설", "자연장지시설", "봉안시설", "묘지현황"]
    with open(os.path.join(ROOT, "facilities_기타.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for sn in other_sheets:
            osws = wb[sn]
            it = osws.iter_rows(values_only=True)
            oh = next(it)
            w.writerow(["시설종류"] + list(oh))
            for r in it:
                w.writerow([sn] + list(r))

    # ---- 화장시설 -> crematorium.csv (1차: 시도별 안내 페이지용, 깨끗한 스키마) ----
    cws = wb["화장시설"]
    cit = cws.iter_rows(values_only=True)
    chdr = next(cit)
    cidx = {h: i for i, h in enumerate(chdr)}
    crem_rows = []
    for r in cit:
        cname = clean_str(r[cidx["시설명"]])
        if not cname:
            continue
        cgongsa = clean_str(r[cidx["공설/사설"]])
        crem_rows.append({
            "sido": clean_str(r[cidx["시도"]]), "sigungu": clean_str(r[cidx["시군구"]]),
            "name": cname, "address": clean_str(r[cidx["주소"]]), "phone": clean_str(r[cidx["전화번호"]]),
            "parking": clean_num(r[cidx["주차대수"]]), "furnaces": clean_num(r[cidx["화장로수"]]),
            "extras": "·".join(f for f in ["식당", "매점", "주차장", "유족대기실", "장애인편의시설"]
                                if clean_str(r[cidx[f]]) == "설치"),
            "type": cgongsa, "map": "",
        })
    with open(os.path.join(ROOT, "crematorium.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sido", "sigungu", "name", "address", "phone",
                                           "parking", "furnaces", "extras", "type", "map"])
        w.writeheader()
        w.writerows(crem_rows)

    # ---- 결측률/시도별 집계 ----
    by_sido = defaultdict(int)
    missing = defaultdict(int)
    for row in out_rows:
        by_sido[row["sido"]] += 1
        for f in ["address", "phone", "rooms", "parking"]:
            if not row[f]:
                missing[f] += 1

    baseline = {
        "경기도": 185, "전라남도": 130, "경상남도": 121, "경상북도": 121, "충청남도": 76, "전북특별자치도": 74,
        "서울특별시": 61, "대구광역시": 56, "부산광역시": 55, "강원특별자치도": 53, "충청북도": 52, "인천광역시": 35,
        "광주광역시": 26, "대전광역시": 19, "울산광역시": 17, "제주특별자치도": 11, "세종특별자치시": 6,
    }

    total = len(out_rows)
    lines = []
    lines.append("# 변환리포트\n")
    lines.append(f"총 시설 수: **{total}**  (기준선 1,098)\n")
    lines.append("## 시도별 시설 수 (기준선 대조)\n")
    lines.append("| 시도 | 변환 결과 | 기준선 | 차이 | 경고 |")
    lines.append("|---|---|---|---|---|")
    all_sido = sorted(set(by_sido) | set(baseline))
    for sd in all_sido:
        got = by_sido.get(sd, 0)
        base = baseline.get(sd, 0)
        diff = got - base
        warn = "⚠️ 20%+ 부족" if base and got < base * 0.8 else ""
        lines.append(f"| {sd} | {got} | {base} | {diff:+d} | {warn} |")

    lines.append("\n## 결측률\n")
    lines.append("| 컬럼 | 결측 수 | 결측률 |")
    lines.append("|---|---|---|")
    for f in ["address", "phone", "rooms", "parking"]:
        cnt = missing[f]
        lines.append(f"| {f} | {cnt} | {cnt/total*100:.1f}% |")

    lines.append(f"\n## 중복 처리 ({len(dup_report)}건 — 동명이지역, 시군구명 접두)\n")
    for d in dup_report:
        lines.append(f"- {d}")
    if not dup_report:
        lines.append("- 없음")

    lines.append(f"\n## 명칭 정규화 변경 내역 ({len(change_notes)}건 — 법인표기·특수문자 삭제, 지점 인라인화, 장례식장 어미 자동 추가)\n")
    for n in change_notes:
        lines.append(f"- {n}")
    if not change_notes:
        lines.append("- 없음")

    with open(os.path.join(ROOT, "변환리포트.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"facilities.csv: {total}행")
    print(f"동명이지역 처리: {len(dup_report)}건")
    print(f"명칭 정규화 변경: {len(change_notes)}건")


if __name__ == "__main__":
    main()
