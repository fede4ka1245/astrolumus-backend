from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Complaint(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    user = models.ForeignKey(User, related_name="complaints", on_delete=models.CASCADE)
    content_object = GenericForeignKey("content_type", "object_id")
    details = models.TextField(verbose_name='Текст жалобы')
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    assigned_employee = models.ForeignKey(User, related_name="assigned_complaints", null=True, blank=True,
                                          on_delete=models.CASCADE)
    status_choices = [
        (1, 'На рассмотрении'),
        (2, 'Разрешена'),
        (3, 'Отклонена')
    ]
    status = models.IntegerField(choices=status_choices, default=1)

    def __str__(self):
        return self.details[:50]

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"
        ordering = ['-updated_at']


class Feedback(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="complaints_feedback", on_delete=models.CASCADE)
    content = models.TextField(max_length=120)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    def __str__(self):
        return '{}-{}'.format(self.complaint.details, str(self.user.username))

    class Meta:
        verbose_name = "Ответ на жалобу"
        verbose_name_plural = "Ответы на жалобы"
        ordering = ['-updated_at']
