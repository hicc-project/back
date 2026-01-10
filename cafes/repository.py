# db/repository.py (PostgreSQL + Django ORM 버전)
from __future__ import annotations

from typing import Dict, Optional
from django.db import transaction

from cafes.models import Place, PlaceDetail, OpenStatusLog


@transaction.atomic
def upsert_place(place: Dict) -> Place:
    """
    places upsert (kakao_id 기준)
    - SQLite raw SQL 대신 Django ORM update_or_create 사용
    """
    kakao_id = str(place.get("kakao_id") or "")
    if not kakao_id:
        raise ValueError("kakao_id is required")

    defaults = {
        "name": place.get("name"),
        "address": place.get("address"),
        "road_address": place.get("road_address"),
        "phone": place.get("phone"),
        "place_url": place.get("place_url"),
        "lat": place.get("lat"),
        "lng": place.get("lng"),
    }

    obj, _created = Place.objects.update_or_create(
        kakao_id=kakao_id,
        defaults=defaults,
    )
    return obj


@transaction.atomic
def insert_place_detail(detail: Dict) -> PlaceDetail:
    """
    place_details insert (스냅샷)
    - Place FK 연결 후 PlaceDetail row 생성
    """
    kakao_id = str(detail.get("kakao_id") or "")
    if not kakao_id:
        raise ValueError("kakao_id is required")

    # Place가 없으면 만들거나(최소한의 Place) 먼저 upsert를 호출하는 구조로 가도 됨
    place, _ = Place.objects.get_or_create(kakao_id=kakao_id, defaults={"name": None})

    obj = PlaceDetail.objects.create(
        place=place,
        rating=detail.get("rating"),
        review_count=detail.get("review_count"),
        holiday_desc=detail.get("holiday_desc"),
        opening_hours_text=detail.get("opening_hours_text"),
        opening_hours_json=detail.get("opening_hours_json"),
    )
    return obj


@transaction.atomic
def insert_open_status_log(row: Dict) -> OpenStatusLog:
    """
    open_status_logs insert
    """
    kakao_id = str(row.get("kakao_id") or "")
    if not kakao_id:
        raise ValueError("kakao_id is required")

    place, _ = Place.objects.get_or_create(kakao_id=kakao_id, defaults={"name": row.get("name")})

    obj = OpenStatusLog.objects.create(
        place=place,
        name=row.get("name"),
        is_open_now=row.get("is_open_now"),  # BooleanField(null=True)
        today_open_time=row.get("today_open_time"),
        today_close_time=row.get("today_close_time"),
        minutes_to_close=row.get("minutes_to_close"),
        today_status_note=row.get("today_status_note"),
    )
    return obj
