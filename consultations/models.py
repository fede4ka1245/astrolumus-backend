from django.conf import settings
from django.db import models


class Consultation(models.Model):
    STATUS_CHOICES = [
        ("new", "Новая"),
        ("in_progress", "В работе"),
        ("done", "Завершена"),
        ("cancelled", "Отменена"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="consultations",
        verbose_name="пользователь",
    )
    name = models.CharField("имя", max_length=255)
    contact = models.CharField("контакт (email или телефон)", max_length=255)
    topic = models.CharField("тема / тип услуги", max_length=255, blank=True)
    message = models.TextField("пожелания", blank=True)
    preferred_time = models.CharField("желаемое время", max_length=255, blank=True)
    status = models.CharField(
        "статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )
    created_at = models.DateTimeField("дата создания", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Заявка на консультацию"
        verbose_name_plural = "Заявки на консультацию"

    def __str__(self):
        return f"{self.name} ({self.created_at:%Y-%m-%d %H:%M})"
