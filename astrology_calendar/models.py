from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth import get_user_model
from django.db import models
from django_minio_backend import MinioBackend
# from sorl.thumbnail import ImageField

User = get_user_model()


def upload_to(instance, filename):
    return 'images/events/{filename}'.format(filename=filename)


class Event(models.Model):
    class Permissions(models.IntegerChoices):
        PRIVATE = 0, "Частный"
        PUBLIC = 1, "Публичный"

    user_dst = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_dst_events"
    )
    user_src = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="user_src_events",
        null=True,
        blank=True,
    )
    title = models.CharField("Название события", max_length=255)
    description = RichTextUploadingField(verbose_name="Описание", null=True, blank=True)
    image = models.ImageField(storage=MinioBackend(bucket_name='forum'), upload_to=upload_to, null=True, blank=True)

    access_type = models.PositiveIntegerField(
        choices=Permissions.choices, verbose_name="Тип доступа"
    )
    event_date = models.DateTimeField(verbose_name="Дата события")

    def __str__(self):
        return self.title

    class Meta:
        db_table = "events"
        verbose_name = "Событие"
        verbose_name_plural = "События"
