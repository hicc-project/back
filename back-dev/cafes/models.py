from django.db import models


class Place(models.Model):
    """
    카페 기본 정보
    - kakao_id를 PK로 사용
    - 테이블명은 Django 기본 규칙: cafes_place
    """
    kakao_id = models.CharField(max_length=32, primary_key=True)

    name = models.CharField(max_length=200, null=True, blank=True)

    address = models.TextField(null=True, blank=True)
    road_address = models.TextField(null=True, blank=True)
    phone = models.TextField(null=True, blank=True)
    place_url = models.TextField(null=True, blank=True)

    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name or self.kakao_id


class PlaceDetail(models.Model):
    """
    카페 상세 스냅샷
    - 테이블명: cafes_placedetail
    - Place 1 : N PlaceDetail
    """
    id = models.BigAutoField(primary_key=True)

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="details",
    )

    rating = models.FloatField(null=True, blank=True)
    review_count = models.IntegerField(null=True, blank=True)
    holiday_desc = models.TextField(null=True, blank=True)

    opening_hours_text = models.TextField(null=True, blank=True)
    opening_hours_json = models.TextField(null=True, blank=True)  # (추후 JSONField 추천)

    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["place", "-fetched_at"]),
        ]


class OpenStatusLog(models.Model):
    """
    현재 영업 상태 로그
    - 테이블명: cafes_openstatuslog
    - Place 1 : N OpenStatusLog
    """
    id = models.BigAutoField(primary_key=True)

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )

    # 스냅샷 당시 이름(Place.name이 변경될 수도 있으니 기록용)
    name = models.TextField(null=True, blank=True)

    # 미정(None)/영업중(True)/영업종료(False)
    is_open_now = models.BooleanField(null=True, blank=True)

    today_open_time = models.TextField(null=True, blank=True)
    today_close_time = models.TextField(null=True, blank=True)

    minutes_to_close = models.IntegerField(null=True, blank=True)

    today_status_note = models.TextField(null=True, blank=True)

    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["place", "-checked_at"]),
            models.Index(fields=["-checked_at"]),
        ]

class Cafe24h(models.Model):
    """
    24시간 카페 캐시/인덱스 테이블
    - Place 1 : 1 (하루 기준이면 날짜 포함 권장)
    """
    id = models.BigAutoField(primary_key=True)

    place = models.OneToOneField(
        Place,
        on_delete=models.CASCADE,
        related_name="cafe24h",
    )

    name = models.TextField(null=True, blank=True)

    # "24시간 판정 기준"이 되는 오늘 시간
    today_open_time = models.TextField(null=True, blank=True)
    today_close_time = models.TextField(null=True, blank=True)

    checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cafes_cafe24h"