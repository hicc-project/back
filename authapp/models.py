from django.db import models
from django.conf import settings

class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )
    cafe_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "cafe_name")  # 같은 유저가 같은 카페 중복 저장 방지
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.cafe_name}"
