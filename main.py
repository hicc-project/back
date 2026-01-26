import time
import json
from datetime import datetime

from config.settings import HOME_LAT, HOME_LNG, RADIUS_M, REQUEST_SLEEP_SEC
from config.settings import KAKAO_REST_KEY, HTTP_TIMEOUT_SEC

from kakao.kakao_local import kakao_search_category
from kakao.kakao_panel3 import fetch_panel3

from parser.cafe_open_hours import parse_from_panel3
from parser.status_calculator import compute_open_now_and_remaining

from db.connection import get_connection
from cafes.repository import upsert_place, insert_place_detail, insert_open_status_log


def main():
    print("📌 Kakao Local API로 반경 내 카페 목록 수집 시작...")
    docs = kakao_search_category(
        lat=HOME_LAT,
        lng=HOME_LNG,
        radius=RADIUS_M,
        category_code="CE7",
        size=15,
        max_pages=10,
    )

    print(f"✅ 수집된 카페 수: {len(docs)}")

    conn = get_connection()
    now = datetime.now()

    try:
        for i, d in enumerate(docs, start=1):
            kakao_id = str(d.get("id"))
            name = d.get("place_name")

            place_row = {
                "kakao_id": kakao_id,
                "name": name,
                "address": d.get("address_name"),
                "road_address": d.get("road_address_name"),
                "phone": d.get("phone"),
                "place_url": d.get("place_url"),
                "lat": float(d.get("y")) if d.get("y") else None,
                "lng": float(d.get("x")) if d.get("x") else None,
            }

            # 1) places upsert
            upsert_place(conn, place_row)

            # 2) panel3 상세 수집 + 저장
            try:
                panel = fetch_panel3(kakao_id)

                parsed = parse_from_panel3(panel)  # detail_opening_hours, rating 등
                live = compute_open_now_and_remaining(panel, now)

                detail_row = {
                    "kakao_id": kakao_id,
                    "rating": parsed.get("detail_rating"),
                    "review_count": parsed.get("detail_review_cnt"),
                    "holiday_desc": parsed.get("detail_holiday"),
                    "opening_hours_text": parsed.get("detail_opening_hours"),
                    "opening_hours_json": json.dumps(panel.get("open_hours"), ensure_ascii=False),
                }
                insert_place_detail(conn, detail_row)

                status_row = {
                    "kakao_id": kakao_id,
                    "name": name,
                    "is_open_now": None if live.get("is_open_now") is None else (1 if live.get("is_open_now") else 0),
                    "today_open_time": live.get("today_open_time"),     # 'HH:MM' or None
                    "today_close_time": live.get("today_close_time"),   # 'HH:MM' or None
                    "today_status_note": live.get("today_status_note"), # 텍스트 or None
                    "minutes_to_close": live.get("minutes_to_close"),
                }
                insert_open_status_log(conn, status_row)

                print(f"[{i}/{len(docs)}] ✅ {name}")

            except Exception as e:
                print(f"[{i}/{len(docs)}] ⚠️ panel3 FAIL {name} ({kakao_id}) | {e}")

            time.sleep(REQUEST_SLEEP_SEC)

        conn.commit()
        print("✅ DB 저장 완료! (commit 완료)")

    finally:
        conn.close()
        print("✅ DB 연결 종료")


if __name__ == "__main__":
    main()
