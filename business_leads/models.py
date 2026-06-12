from django.db import models


class BusinessLead(models.Model):
    """Заявка с B2B-лендинга /business («оставить контакты»)."""

    name = models.CharField("Имя", max_length=120)
    contact = models.CharField("Контакт (телефон / Telegram / email)", max_length=200)
    comment = models.TextField("Комментарий", blank=True, default="")
    source = models.CharField("Источник", max_length=64, blank=True, default="business-landing")
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    is_processed = models.BooleanField("Обработана", default=False)

    class Meta:
        verbose_name = "B2B-заявка"
        verbose_name_plural = "B2B-заявки"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} — {self.contact}"
