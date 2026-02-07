from django.db import models

from django.conf import settings
from django.contrib.contenttypes.fields import ContentType, GenericForeignKey


class Favorite(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="favorites",
        on_delete=models.CASCADE,
        verbose_name="автор",
    )
    created_at = models.DateTimeField("дата и время создания", auto_now_add=True)

    class Meta:
        unique_together = ["content_type", "object_id", "author"]
        verbose_name = verbose_name_plural = "избранное"

    def __str__(self):
        return f"Избранное {self.author}"
