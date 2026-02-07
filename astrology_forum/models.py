from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django_minio_backend import MinioBackend

from ckeditor_uploader.fields import RichTextUploadingField
from ordered_model.models import OrderedModel

from complaints.models import Complaint
from favorite.models import Favorite
from horoscope.models import FullHoroscope

User = get_user_model()


class Category(OrderedModel):
    title = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        related_name="children",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title

    order_with_respect_to = 'parent_id'

    class Meta:
        db_table = "categories"
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ('-parent_id', 'order')


def upload_to(instance, filename):
    return 'images/forum/{filename}'.format(filename=filename)


# TODO create management command to remove images that not attached to the Topic (in e.g. 12 last hours)
class Image(models.Model):
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True, editable=True)
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="forum_images")
    image = models.ImageField("Фото превью", storage=MinioBackend(bucket_name='forum'), upload_to=upload_to)
    image_original = models.ImageField("Фото оригинал", storage=MinioBackend(bucket_name='forum'), upload_to=upload_to)

    def __str__(self):
        return f"Фото id {self.pk}"

    class Meta:
        verbose_name = "Фото топика"
        verbose_name_plural = "Фото топиков"


class Topic(models.Model):
    class AccessLevel(models.IntegerChoices):
        PRIVATE = 0, "Приватный"
        PUBLIC = 1, "Публичный"

    class Status(models.TextChoices):
        NOT_CHECKED = "not_checked", "Не проверена"
        ACCEPTED = "accepted", "Допущена"
        ARCHIVE = "archive", "В архиве"
        BLOCKED = "blocked", "Заблокирована"
        TEMPORARY_BLOCKED = "temporary_blocked", "Временно заблокирована"

    title = models.CharField(verbose_name="Название топика", max_length=255)
    description = RichTextUploadingField(verbose_name="Описание", max_length=10000, null=True, blank=True)
    images = models.ManyToManyField(Image, related_name="topics", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    published_at = models.DateTimeField("Опубликован", null=True, blank=True, editable=True,
                                        help_text="Дата публикации, при отсутствии даты, топик не показывается")
    moderated_at = models.DateTimeField("Проверен", null=True, blank=True, editable=True,
                                        help_text="Дата проверки топика модератором")
    moderated_by = models.ForeignKey(User, related_name="moderated_topics", on_delete=models.CASCADE, null=True,
                                     blank=True)
    moderator_comment = models.TextField("Комментарий модератора", null=True, blank=True)

    user = models.ForeignKey(User, verbose_name="Автор", related_name="user_topics", on_delete=models.CASCADE)
    access_level = models.PositiveIntegerField(
        choices=AccessLevel.choices, verbose_name="Уровень доступа", default=1,
    )
    status = models.CharField(
        choices=Status.choices, verbose_name="Статус", max_length=25,
        default=Status.NOT_CHECKED
    )
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        related_name="topics",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # invited = models.ManyToManyField(User, blank=True)
    members = models.ManyToManyField(User,
                                     verbose_name="Участники",
                                     through='Membership',
                                     through_fields=('topic', 'user'),
                                     ),
    horoscope_link = models.URLField("Ссылка на гороскоп", max_length=255,  null=True, blank=True)
    dim_sky = models.BooleanField(default=False)
    # show = models.BooleanField(default=False)
    horoscope = models.ForeignKey(
        FullHoroscope,
        related_name="horoscope_topics",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    favorites = GenericRelation(Favorite, related_query_name='topic')

    def __str__(self):
        return self.title

    class Meta:
        db_table = "topics"
        verbose_name = "Топик"
        verbose_name_plural = "Топики"
        ordering = ['-updated_at']


class Membership(models.Model):
    class Status(models.TextChoices):
        NEW = "invited", "Приглашен"
        ACCEPTED = "accepted", "Принят"
        REJECTED = "rejected", "Отклонен"

    class UserStatus(models.TextChoices):
        NEW = "invited", "Приглашен"
        ACCEPTED = "accepted", "Принял"
        REJECTED = "rejected", "Отклонил"

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    inviter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="membership_invites",
    )
    invite_reason = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        choices=Status.choices, verbose_name="Статус автора темы", max_length=25,
        default=Status.NEW
    )
    user_status = models.CharField(
        choices=UserStatus.choices, verbose_name="Статус приглашенного пользователя", max_length=25,
        default=UserStatus.NEW
    )

    def __str__(self):
        return f"{self.topic} / {self.user}"

    class Meta:
        verbose_name = "Участник топика"
        verbose_name_plural = "Участники топиков"
        ordering = ['-created_at']
        unique_together = ["user", "topic"]


class Comment(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Ждет проверки"
        ACCEPTED = "accepted", "Допущен"
        BLOCKED = "blocked", "Заблокирован"

    user = models.ForeignKey(
        User, related_name="user_comments", on_delete=models.CASCADE
    )
    # text = RichTextUploadingField(verbose_name="Текст комментария", max_length=3000, null=True, blank=True)
    text = models.TextField(verbose_name="Текст комментария", max_length=3000, null=True, blank=True)
    image = models.ForeignKey(Image, related_name="comments", on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey(
        Topic,
        related_name="comments",
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        "self",
        related_name="comment_comments",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Родительский комментарий"
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True, editable=True)
    status = models.CharField(
        choices=Status.choices, verbose_name="Статус", max_length=25,
        default=Status.NEW
    )
    moderated_at = models.DateTimeField("Проверен", null=True, blank=True, editable=True,
                                        help_text="Дата проверки топика модератором")
    moderated_by = models.ForeignKey(User, related_name="moderated_comments", on_delete=models.CASCADE, null=True,
                                     blank=True)
    moderator_comment = models.TextField("Комментарий модератора", null=True, blank=True)
    complaint = GenericRelation(Complaint, related_query_name='comment')

    def __str__(self):
        return self.text[:150] + "..."

    class Meta:
        db_table = "comments"
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"


class LastTopicCommentRead(models.Model):
    user = models.ForeignKey(
        User, related_name="topics_unread_count", on_delete=models.CASCADE
    )
    topic = models.ForeignKey(
        Topic, related_name="user_unread_count", on_delete=models.CASCADE
    )
    last_user_comment_seen = models.ForeignKey(
        Comment, related_name="user_last_unread_comment", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.topic} / {self.user} / {self.last_user_comment_seen}"

    class Meta:
        verbose_name = "Последний прочитанный комментарий"
        verbose_name_plural = "Последние прочитанные комментарии"


class ForumRules(models.Model):
    title = models.CharField(verbose_name="Название правил", max_length=255)
    description = RichTextUploadingField(verbose_name="Описание")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True, editable=True)
    published_at = models.DateTimeField("Опубликован", editable=True,
                                        help_text="Используется последняя опубликованная редакция")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-published_at", "-updated_at"]
        verbose_name = "Правила форума"
        verbose_name_plural = "Правила форума"
