import time
from datetime import datetime

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.models import Group as BaseGroup
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

from django_minio_backend import MinioBackend


from rest_framework_simplejwt.tokens import RefreshToken

from utils.models_utils import generate_new_password


def get_last_seen_cache_key(user):
    """
        Get cache database to cache last database write timestamp
    """
    return "last_seen:%s" % (user.pk,)


def user_seen(user):
    cache_key = get_last_seen_cache_key(user)
    # compute limit to update db
    limit = time.time() - settings.LAST_SEEN_INTERVAL
    seen = cache.get(cache_key)
    if not seen or seen < limit:
        # mark the database and the cache, if interval is cleared force
        # database write
        user.last_seen = now()
        user.save()
        timeout = settings.LAST_SEEN_INTERVAL
        cache.set(cache_key, time.time(), timeout)


class UserManager(BaseUserManager):
    """
    Overrides the stock user manager to use `email` instead of `username`.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The phone number must be set")
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def with_perm(
            self, perm, is_active=True, include_superusers=True, backend=None, obj=None
    ):
        if backend is None:
            backends = auth._get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    "You have multiple authentication backends configured and "
                    "therefore must provide the `backend` argument."
                )
        elif not isinstance(backend, str):
            raise TypeError(
                "backend must be a dotted import path string (got %r)." % backend
            )
        else:
            backend = auth.load_backend(backend)
        if hasattr(backend, "with_perm"):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()


class Settings(models.Model):
    language = models.CharField(max_length=10, default='en')
    arudha_scheme = models.IntegerField(default=1)


class AppLanguage(models.Model):
    name = models.CharField(_("name"), max_length=255)
    code = models.CharField(_("language code"), max_length=32, unique=True)
    enabled = models.BooleanField(_("enabled"), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Язык приложения"
        verbose_name_plural = "Языки приложения"


class User(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)

    first_name = models.CharField(_("first name"), max_length=150, blank=False, null=False)
    last_name = models.CharField(_("last name"), max_length=150, blank=False, null=False)
    patronymic = models.CharField(_("patronymic"), max_length=150, blank=True, null=True)
    language = models.CharField(
        _("preferred UI language"),
        max_length=15,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    app_language = models.ForeignKey(
        settings.APP_LANGUAGE_MODEL,
        verbose_name=_("application language"),
        related_name="users",
        on_delete=models.RESTRICT,
    )
    last_seen = models.DateTimeField(blank=True, null=True)
    settings = models.OneToOneField(
        Settings,
        related_name='settings',
        on_delete=models.CASCADE,
        default=None,
        null=True,
    )
    complaint = GenericRelation("complaints.Complaint", related_query_name='users')

    consent_personal_data = models.BooleanField(
        "Согласие на обработку персональных данных",
        default=False,
    )
    consent_marketing = models.BooleanField(
        "Согласие на маркетинговую рассылку",
        default=False,
    )
    consent_marketing_date = models.DateTimeField(
        "Дата согласия на рассылку",
        blank=True,
        null=True,
    )

    # same as tariffs model
    restriction_forum = models.BooleanField("Форум отключен", default=False,
                                            help_text="Отключить форум пользователю")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]
    EMAIL_FIELD = "email"

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def nickname(self):
        return str(self)

    def get_full_name(self):
        return f"{self.first_name} {self.patronymic} {self.last_name}"

    def generate_tokens(self):
        expires_in = int(
            datetime.timestamp(timezone.now() + settings.ACCESS_TOKEN_LIFETIME)
        )

        refresh_token = RefreshToken.for_user(self)

        refresh = str(refresh_token)
        access = str(refresh_token.access_token)

        return {
            "access": access,
            "refresh": refresh,
            "expires_in": expires_in,
            "email": self.email,
        }

    class Meta:
        ordering = ["-id"]
        verbose_name = _("user")
        verbose_name_plural = _("users")


class Group(BaseGroup):
    class Meta:
        proxy = True
        verbose_name = _("group")
        verbose_name_plural = _("groups")


class GeneratedPassword(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    password = models.CharField(
        default=generate_new_password, editable=False, max_length=8
    )
    attempts = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date", "is_active"]
        verbose_name = "временный пароль"
        verbose_name_plural = "временные пароли"

    def __str__(self):
        return f"Generated password for {str(self.user)}"


def user_image_upload_to(instance, filename):
    return 'images/files/{filename}'.format(filename=filename)


class UserFile(models.Model):
    class FileType(models.IntegerChoices):
        PHOTO = 0, "Фото"
        CERTIFICATE = 1, "Сертификат"

    user = models.ForeignKey(User, related_name="user_files", on_delete=models.CASCADE)
    image = models.ImageField("Фото превью", storage=MinioBackend(bucket_name='users'), upload_to=user_image_upload_to)
    image_original = models.ImageField("Фото оригинал", storage=MinioBackend(bucket_name='users'), upload_to=user_image_upload_to)

    file_type = models.PositiveIntegerField(
        choices=FileType.choices, verbose_name="Тип файла"
    )

    def __str__(self):
        return f"Файл {self.id} от {self.user.nickname}"

    class Meta:
        db_table = "user_files"
        verbose_name = "Файл пользователя"
        verbose_name_plural = "Файлы пользователей"


def upload_to(instance, filename):
    return 'images/avatars/{filename}'.format(filename=filename)


class UserProfile(models.Model):
    class UserRole(models.IntegerChoices):
        COMMON_USER = 0, "Обычный пользователь"
        SCHOOL_ADMINISTRATOR = 1, "Администратор школы"

    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    about = models.TextField(blank=True, null=True, verbose_name="Расскажите о себе")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Дата рождения")

    full_show = models.BooleanField(
        default=True, verbose_name="Показывать профиль полностью или сокращенно"
    )
    user_notifications = models.BooleanField(
        default=True, verbose_name="Уведомления от пользователей"
    )
    calendar = models.BooleanField(default=True, verbose_name="Календарь")
    astro_processor = models.BooleanField(default=True, verbose_name="Астро процессор")
    forum = models.BooleanField(default=True, verbose_name="Форум")
    user_role = models.PositiveIntegerField(
        choices=UserRole.choices,
        verbose_name="Роль пользователя",
        default=UserRole.COMMON_USER.value,
    )
    avatar = models.ImageField(storage=MinioBackend(bucket_name='users'), upload_to=upload_to, null=True, blank=True)
    teacher_title = models.CharField(max_length=255, null=True, blank=True)
    teacher_description = models.TextField(null=True, blank=True)

    complaint = GenericRelation("complaints.Complaint", related_query_name='user_profile')

    def __str__(self):
        return f"Профиль пользователя {self.user.nickname}"

    class Meta:
        db_table = "user_profiles"
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


class Subscription(models.Model):
    class Statuses(models.IntegerChoices):
        AWAITING = 0, "Ожидает"
        ACCEPTED = 1, "Принят"
        REJECTED = 2, "Отклонен"

    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    user_dst = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_dst_subscriptions"
    )
    user_src = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_src_subscriptions"
    )
    status = models.PositiveIntegerField(
        choices=Statuses.choices, default=Statuses.ACCEPTED.value
    )

    class Meta:
        db_table = "subscriptions"
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        unique_together = [['user_dst', 'user_src']]


class BlockedUser(models.Model):
    user_dst = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_dst_blocked_users"
    )
    user_src = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_src_blocked_users"
    )

    class Meta:
        db_table = "blocked_users"
        verbose_name = "Заблокированный пользователь"
        verbose_name_plural = "Заблокированные пользователи"
