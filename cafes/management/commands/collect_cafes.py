import json
import time
from datetime import datetime

from django.core.management.base import BaseCommand

from config.settings import HOME_LAT, HOME_LNG, RADIUS_M, REQUEST_SLEEP_SEC
from kakao.kakao_local import kakao_search_category
from kakao.kakao_panel3 import fetch_panel3
from parser.cafe_open_hours import parse_from_panel3
from parser.status_calculator import compute_open_now_and_remaining

from cafes.models import Place, PlaceDetail, OpenStatusLog


class Command(BaseCommand):
    help = "Kakao Local API로 주변 카페를 수집하고 Place/PlaceDetail/OpenStatusLog에 저장합니다."

    def handle(self, *args, **options):
        self.stdout.write("📌 Kakao Local API로 반경 내 카페 목록 수집 시작...")

        docs = kakao_search_category(
            lat=HOME_LAT,
            lng=HOME_LNG,
            radius=RADIUS_M,
            category_code="CE7",
            size=15,
            max_pages=10,
        )

        self.stdout.write(f"✅ 수집된 카페 수: {len(docs)}")
        now = datetime.now()

        for i, d in enumerate(docs, start=1):
            kakao_id = str(d.get("id"))
            name = d.get("place_name")

            # 1) Place upsert (kakao_id가 PK라 update_or_create가 딱 맞음)
            place_defaults = {
                "name": name,
                "address": d.get("address_name"),
                "road_address": d.get("road_address_name"),
                "phone": d.get("phone"),
                "place_url": d.get("place_url"),
                "lat": float(d.get("y")) if d.get("y") else None,
                "lng": float(d.get("x")) if d.get("x") else None,
            }
            place, _created = Place.objects.update_or_create(
                kakao_id=kakao_id,
                defaults=place_defaults,
            )

            # 2) panel3 상세 수집 + 스냅샷 저장
            try:
                panel = fetch_panel3(kakao_id)

                parsed = parse_from_panel3(panel)
                live = compute_open_now_and_remaining(panel, now)

                PlaceDetail.objects.create(
                    place=place,
                    rating=parsed.get("detail_rating"),
                    review_count=parsed.get("detail_review_cnt"),
                    holiday_desc=parsed.get("detail_holiday"),
                    opening_hours_text=parsed.get("detail_opening_hours"),
                    opening_hours_json=json.dumps(panel.get("open_hours"), ensure_ascii=False),
                )

                OpenStatusLog.objects.create(
                    place=place,
                    name=name,
                    is_open_now=live.get("is_open_now"),  # BooleanField(null=True)라 그대로 넣으면 됨
                    today_open_time=live.get("today_open_time"),
                    today_close_time=live.get("today_close_time"),
                    today_status_note=live.get("today_status_note"),
                    minutes_to_close=live.get("minutes_to_close"),
                )

                self.stdout.write(f"[{i}/{len(docs)}] ✅ {name}")

            except Exception as e:
                self.stdout.write(f"[{i}/{len(docs)}] ⚠️ panel3 FAIL {name} ({kakao_id}) | {e}")

            time.sleep(REQUEST_SLEEP_SEC)

        self.stdout.write("✅ 완료!")
