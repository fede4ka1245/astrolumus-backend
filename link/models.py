from django.db import models
import uuid


class Link(models.Model):
    link = models.CharField(max_length=512)
    link_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        db_table = "link"
        verbose_name = "link"
        verbose_name_plural = "link"

    def __str__(self):
        return self.link_uid
    