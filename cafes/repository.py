# db/repository.py (PostgreSQL + Django ORM 버전)
from __future__ import annotations

from typing import Dict, List
from django.db import transaction

from cafes.models import Place, PlaceDetail, OpenStatusLog


@transaction.atomic
def upsert_place(place: Dict) -> Place:
    """
    places upsert (kakao_id 기준)
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
    place_details insert (스냅샷) - 단건용(기존 유지)
    """
    kakao_id = str(detail.get("kakao_id") or "")
    if not kakao_id:
        raise ValueError("kakao_id is required")

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
def bulk_insert_place_details(rows: List[Dict], batch_size: int = 200) -> int:
    """
    place_details 대량 insert (collect_details 최적화용)

    rows: [
      {
        "kakao_id": "...",
        "rating": ...,
        "review_count": ...,
        "holiday_desc": ...,
        "opening_hours_text": ...,
        "opening_hours_json": ...,
      }, ...
    ]

    ✅ 핵심 최적화
    - Place를 in_bulk로 한 번에 가져오고
    - 없는 Place는 bulk_create로 한 번에 만들고
    - PlaceDetail은 bulk_create로 한 번에 insert
    """
    if not rows:
        return 0

    # 1) kakao_id 정리 + 유효한 row만
    clean: List[Dict] = []
    for r in rows:
        kid = str(r.get("kakao_id") or "").strip()
        if kid:
            r["kakao_id"] = kid
            clean.append(r)
    if not clean:
        return 0

    kakao_ids = list({r["kakao_id"] for r in clean})
    places_map = Place.objects.in_bulk(kakao_ids, field_name="kakao_id")  # {kakao_id: Place}

    missing = [kid for kid in kakao_ids if kid not in places_map]
    if missing:
        Place.objects.bulk_create(
            [Place(kakao_id=kid, name=None) for kid in missing],
            batch_size=batch_size,
            ignore_conflicts=True,
        )
        places_map.update(Place.objects.in_bulk(missing, field_name="kakao_id"))

    # 4) PlaceDetail 객체 모아서 bulk_create
    objs: List[PlaceDetail] = []
    for r in clean:
        place = places_map.get(r["kakao_id"])
        if not place:
            # 이론상 거의 없음(동시성/데이터 이상치 대비)
            continue

        objs.append(
            PlaceDetail(
                place=place,
                rating=r.get("rating"),
                review_count=r.get("review_count"),
                holiday_desc=r.get("holiday_desc"),
                opening_hours_text=r.get("opening_hours_text"),
                opening_hours_json=r.get("opening_hours_json"),
            )
        )

    if not objs:
        return 0

    PlaceDetail.objects.bulk_create(objs, batch_size=batch_size)
    return len(objs)


@transaction.atomic
def insert_open_status_log(row: Dict) -> OpenStatusLog:
    place = row.get("place")
    if place is None:
        kakao_id = str(row.get("kakao_id") or "")
        if not kakao_id:
            raise ValueError("place or kakao_id is required")
        place, _ = Place.objects.get_or_create(
            kakao_id=kakao_id,
            defaults={"name": row.get("name")}
        )

    return OpenStatusLog.objects.create(
        place=place,
        name=row.get("name"),
        is_open_now=row.get("is_open_now"),
        today_open_time=row.get("today_open_time"),
        today_close_time=row.get("today_close_time"),
        minutes_to_close=row.get("minutes_to_close"),
        today_status_note=row.get("today_status_note"),
    )
