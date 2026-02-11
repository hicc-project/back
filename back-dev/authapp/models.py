from django.db import models
from django.conf import settings

class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    place = models.ForeignKey(
        "cafes.Place",
        on_delete=models.CASCADE,
        related_name="bookmarked_by",
        null=False, blank=False,   
    )
    memo = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "place"], name="uniq_user_place_bookmark")
        ]
        ordering = ["-created_at"]

