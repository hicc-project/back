# cafes/views.py
import os
import math
import json
from datetime import datetime

from dotenv import load_dotenv
from django.db.models import OuterRef, Subquery
from rest_framework.decorators import api_view
from rest_framework.response import Response

from kakao.kakao_local import kakao_search_category
from kakao.kakao_panel3 import fetch_panel3

from parser.cafe_open_hours import parse_from_panel3
from parser.status_calculator import compute_open_now_and_remaining

from cafes.repository import upsert_place, bulk_insert_place_details, insert_open_status_log

from cafes.models import Place, PlaceDetail, Cafe24h
from .serializers import PlaceSerializer

import traceback

KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY", "").strip().strip('"').strip("'")


@api_view(["GET"])
def places(request):
    """
    GET /api/places?lat=...&lng=...&radius=...
    - lat/lng/radius가 있으면 주변만(사각형 필터) 반환
    - 없으면 최신 200개 반환
    """
    qp = request.query_params
    lat = qp.get("lat")
    lng = qp.get("lng")
    radius = qp.get("radius") or qp.get("radius_m")

    qs = Place.objects.all()

    if lat and lng and radius:
        lat = float(lat)
        lng = float(lng)
        radius_m = float(radius)

        # 위/경도 기준으로 "대략적인 사각형 필터" (빠름)
        dlat = radius_m / 111000.0
        dlng = radius_m / (111000.0 * math.cos(math.radians(lat)))

        qs = qs.filter(
            lat__isnull=False,
            lng__isnull=False,
            lat__gte=lat - dlat,
            lat__lte=lat + dlat,
            lng__gte=lng - dlng,
            lng__lte=lng + dlng,
        )

    qs = qs.order_by("-created_at")[:200]
    return Response(PlaceSerializer(qs, many=True).data)


@api_view(["POST"])
def collect_places(request):
    """
    POST /api/collect
    body: {lat, lng, radius_m}
    - 카카오에서 수집하고 Place에 upsert
    """
    if not KAKAO_REST_KEY:
        return Response({"error": "KAKAO_REST_KEY missing"}, status=500)

    lat = float(request.data.get("lat", os.getenv("HOME_LAT", "37.5544229")))
    lng = float(request.data.get("lng", os.getenv("HOME_LNG", "126.9295616")))
    radius = int(request.data.get("radius_m", os.getenv("RADIUS_M", "1000")))

    Place.objects.all().delete()


    docs = kakao_search_category(
        lat=lat,
        lng=lng,
        radius=radius,
        category_code="CE7",
        size=15,
        max_pages=3,
    )

    saved = 0
    for d in docs:
        row = {
            "kakao_id": str(d.get("id") or ""),
            "name": d.get("place_name") or d.get("name"),
            "address": d.get("address_name"),
            "road_address": d.get("road_address_name"),
            "phone": d.get("phone"),
            "place_url": d.get("place_url"),
            "lat": float(d.get("y")) if d.get("y") else None,
            "lng": float(d.get("x")) if d.get("x") else None,
        }
        if not row["kakao_id"]:
            continue

        upsert_place(row)
        saved += 1

    return Response({"ok": True, "saved": saved, "fetched": len(docs)})

from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.decorators import api_view
from rest_framework.response import Response
import json

from cafes.models import Place
from cafes.repository import bulk_insert_place_details

@api_view(["POST"])
def collect_details(request):
    limit = int(request.data.get("limit", 200))
    workers = int(request.data.get("workers", 12))  # ✅ 동시 실행 수 조절

    qs = list(
        Place.objects.exclude(place_url__isnull=True)
        .exclude(place_url__exact="")
        .only("kakao_id", "name")
        .order_by("-updated_at")[:limit]
    )

    rows = []
    errors = 0

    def fetch_and_parse(p: Place):
        panel3 = fetch_panel3(p.kakao_id)              # ✅ 네트워크 병목
        detail = parse_from_panel3(panel3)

        return {
            "kakao_id": p.kakao_id,
            "rating": detail.get("detail_rating"),
            "review_count": detail.get("detail_review_cnt"),
            "holiday_desc": detail.get("detail_holiday"),
            "opening_hours_text": detail.get("detail_opening_hours"),
            "opening_hours_json": json.dumps(panel3, ensure_ascii=False),
        }

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fetch_and_parse, p) for p in qs]
        for f in as_completed(futures):
            try:
                rows.append(f.result())
            except Exception as e:
                errors += 1
                print("[collect_details ERROR]", e)

    saved = bulk_insert_place_details(rows, batch_size=200)

    return Response({"ok": True, "saved": saved, "errors": errors, "workers": workers})


@api_view(["POST"])
def refresh_status(request):
    """
    POST /api/refresh_status
    - PlaceDetail(opening_hours_json)의 "최신 스냅샷" 기준으로
      현재 영업 상태 계산 후 OpenStatusLog에 저장 (ORM)
    """
    now = datetime.now()
    print("[refresh_status] HIT", flush=True)

    # Place별 최신 PlaceDetail id (서브쿼리)
    latest_detail_id = Subquery(
        PlaceDetail.objects.filter(place=OuterRef("pk"))
        .order_by("-fetched_at", "-id")
        .values("id")[:1]
    )

    places_qs = (
        Place.objects.annotate(latest_detail_id=latest_detail_id)
        .exclude(latest_detail_id__isnull=True)
        .order_by("-updated_at")[:200]
    )

    latest_ids = [p.latest_detail_id for p in places_qs]
    details_map = PlaceDetail.objects.in_bulk(latest_ids)  # {id: PlaceDetail}

    inserted = 0
    skipped = 0
    errors = 0

    for p in places_qs:
        try:
            d = details_map.get(p.latest_detail_id)
            if not d or not d.opening_hours_json:
                skipped += 1
                continue

            panel_json = d.opening_hours_json

            # TextField면 str, 혹시 dict로 들어온 케이스도 대응
            if isinstance(panel_json, dict):
                panel = panel_json
            else:
                panel = json.loads(panel_json)

            live = compute_open_now_and_remaining(panel, now)

            status_row = {
                "kakao_id": p.kakao_id,
                "name": p.name,
                "is_open_now": live.get("is_open_now"),  # bool/None 그대로
                "today_open_time": live.get("today_open_time"),
                "today_close_time": live.get("today_close_time"),
                "minutes_to_close": live.get("minutes_to_close"),
                "today_status_note": live.get("today_status_note"),
            }

            insert_open_status_log(status_row)
            # ✅ 24시간 카페 판별 & 테이블 업데이트
            open_t = live.get("today_open_time")
            close_t = live.get("today_close_time")

            is_24h = (open_t == "00:00" and close_t in ("23:59", "24:00", "00:00"))

            if is_24h:
                Cafe24h.objects.update_or_create(
                    place=p,
                    defaults={
                        "name": p.name,
                        "today_open_time": open_t,
                        "today_close_time": close_t,
                    },
                )
            else:
                Cafe24h.objects.filter(place=p).delete()
            inserted += 1
            

        except Exception as e:
            errors += 1
            print("[refresh_status ERROR]", p.kakao_id, p.name, e, flush = True)
            traceback.print_exc()
            continue

    return Response(
        {
            "ok": True,
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors,
            "server_now": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
from rest_framework.decorators import api_view
from rest_framework.response import Response
from cafes.models import Cafe24h

@api_view(["GET"])
def cafes_24h(request):
    qs = Cafe24h.objects.select_related("place").order_by("-checked_at")

    data = []
    for x in qs:
        data.append({
            "kakao_id": x.place.kakao_id,
            "name": x.name or x.place.name,
            "lat": x.place.lat,
            "lng": x.place.lng,
            "place_url": x.place.place_url,
            "today_open_time": x.today_open_time,
            "today_close_time": x.today_close_time,
            "checked_at": x.checked_at,
        })

    return Response(data)

from cafes.models import OpenStatusLog
from django.db.models import F
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.db import connection

@api_view(["GET"])
def open_status_logs(request):
    limit_raw = request.query_params.get("limit", "100")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 100

    order = request.query_params.get("order", "id")

    qs = OpenStatusLog.objects.select_related("place")

    if order == "minutes":
        qs = qs.order_by(
            F("minutes_to_close").asc(nulls_last=True)
        )
    else:
        qs = qs.order_by("id")

    qs = qs[:limit]

    data = []
    for log in qs:
        data.append({
            "kakao_id": log.place.kakao_id,
            "name": log.name,
            "is_open_now": log.is_open_now,
            "today_open_time": log.today_open_time,
            "today_close_time": log.today_close_time,
            "minutes_to_close": log.minutes_to_close,
            "today_status_note": log.today_status_note,
            "checked_at": log.checked_at,
        })

    debug = {
        "vendor": connection.vendor,
        "db_name": connection.settings_dict.get("NAME"),
        "db_host": connection.settings_dict.get("HOST"),
    }

    return Response({
        "_debug": debug,
        "data": data,
    })

