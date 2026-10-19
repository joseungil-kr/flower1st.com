import csv
import json
import re
import unittest
from pathlib import Path

import build


class FacilityPageAccuracyTests(unittest.TestCase):
    def test_not_found_page_is_explicit_and_not_indexable(self):
        page = build.not_found_page()
        self.assertIn('<meta name="robots" content="noindex,follow">', page)
        self.assertIn("페이지를 찾을 수 없습니다", page)
        self.assertIn('<a href="/">홈으로 돌아가기</a>', page)

    def test_same_named_goseong_counties_have_distinct_titles(self):
        with (Path(build.ROOT) / "facilities.csv").open(encoding="utf-8-sig", newline="") as handle:
            facilities = list(csv.DictReader(handle))

        by_sido = {
            sido: [row for row in facilities if row.get("sido") == sido and row.get("sigungu") == "고성군"]
            for sido in ("경상남도", "강원특별자치도")
        }
        self.assertTrue(all(by_sido.values()))
        self.assertEqual(1, len({build.sgg_display(sido, "고성군") for sido in by_sido}))

        pages = {}
        old_slugs = {sido: build.SGG_SLUG.get((sido, "고성군")) for sido in by_sido}
        try:
            for sido in by_sido:
                build.SGG_SLUG[(sido, "고성군")] = f"{sido}고성군{build.FN}"
            for sido, rows in by_sido.items():
                slug, page = build.sigungu_page(sido, "고성군", rows, [], {}, include_sido=True)
                title = re.search(r"<title>(.*?)</title>", page)
                self.assertIsNotNone(title)
                pages[sido] = (slug, title.group(1))
                self.assertIn(f"<h1>{sido} 고성군 장례식장 화환</h1>", page)
        finally:
            for sido, slug in old_slugs.items():
                if slug is None:
                    build.SGG_SLUG.pop((sido, "고성군"), None)
                else:
                    build.SGG_SLUG[(sido, "고성군")] = slug

        self.assertNotEqual(pages["경상남도"][0], pages["강원특별자치도"][0])
        self.assertNotEqual(pages["경상남도"][1], pages["강원특별자치도"][1])
        self.assertIn("경상남도 고성군", pages["경상남도"][1])
        self.assertIn("강원특별자치도 고성군", pages["강원특별자치도"][1])

    def test_room_count_and_facility_type_do_not_invent_environment_facts(self):
        rendered = set()
        for facility_type in ("사설(병원)", "공설(병원)", "사설(전문)"):
            for rooms in ("1", "4", "8"):
                row = {
                    "name": "검증용 장례식장",
                    "sido": "서울특별시",
                    "sigungu": "강남구",
                    "rooms": rooms,
                    "parking": "300",
                    "extras": "식당·매점·유족대기실·장애인편의시설",
                    "type": facility_type,
                }
                with self.subTest(facility_type=facility_type, rooms=rooms):
                    guide = build.facility_deep_guide(row)
                    rendered.add(guide)
                    self.assertIn(
                        "빈소 호수와 상주 성함을 함께 알려주세요. "
                        "리본에 넣을 보내시는 분의 이름이나 단체명도 함께 남겨주시면 됩니다.",
                        guide,
                    )
                    for unsupported_claim in (
                        "복도 구획이 체계적으로 분리",
                        "상례 전용 진입로",
                        "하역 구역",
                        "표준화된 화환 거치대",
                        "내원 환자 및 일반 방문객과의 동선",
                        "유족 맞춤형 서비스",
                        "대형 전용 주차 공간",
                        "인근 공영주차장",
                        "독립된 유족대기실",
                        "휠체어 경사로",
                    ):
                        self.assertNotIn(unsupported_claim, guide)
        self.assertEqual(1, len(rendered), "room count/type must not change the general order guidance")

    def test_facility_destination_address_stays_in_body_not_florist_schema(self):
        source = Path(build.ROOT) / "facilities.csv"
        with source.open(encoding="utf-8-sig", newline="") as handle:
            row = next(item for item in csv.DictReader(handle) if item.get("address"))

        slug, page = build.facility_page(row, [], {})
        json_ld_match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', page, flags=re.DOTALL
        )
        self.assertIsNotNone(json_ld_match)
        graph = json.loads(json_ld_match.group(1))["@graph"]
        florist = next(item for item in graph if item.get("@type") == "Florist")

        self.assertNotIn("address", florist)
        self.assertEqual(build.C["brand"], florist["name"])
        self.assertIn(row["address"], page, "facility address remains visible as destination information")
        self.assertIn("주소", page)
        self.assertTrue(any(item.get("@type") == "BreadcrumbList" for item in graph))
        faq = next(item for item in graph if item.get("@type") == "FAQPage")
        self.assertTrue(faq["mainEntity"])
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page)
        self.assertIsNotNone(canonical)
        self.assertEqual(f"https://{build.C['domain']}/{build.enc(slug)}/", canonical.group(1))
        self.assertEqual(canonical.group(1), florist["url"])


if __name__ == "__main__":
    unittest.main()
