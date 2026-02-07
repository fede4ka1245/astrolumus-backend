from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models
from django_minio_backend import MinioBackend
from ordered_model.models import OrderedModel
from sorl.thumbnail import ImageField

from advertising.models import BannerType

User = get_user_model()


class Course(models.Model):
    class CourseType(models.IntegerChoices):
        STEP = 0, "Ступень"
        ADDITIONAL = 1, "Дополнительный"
        MASTER_CLASS = 2, "Мастер класс"
        MINI = 3, "Мини"

    title = models.CharField(verbose_name="Название курса", max_length=255)
    description = RichTextUploadingField(verbose_name="Описание")
    image = ImageField(upload_to="courses", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    course_type = models.PositiveIntegerField(
        choices=CourseType.choices, verbose_name="Тип курса"
    )
    publish_start = models.DateField(verbose_name="Дата начала", null=True, blank=True)
    stage_name = models.CharField(
        verbose_name="Название ступени", max_length=255, null=True, blank=True
    )
    enroll_in_course = models.URLField(
        verbose_name="Записаться на курс", null=True, blank=True
    )
    teachers = models.ManyToManyField(to=User, blank=True)
    duration = models.CharField(
        verbose_name="Продолжительность", max_length=255, null=True, blank=True
    )
    nominal_certificate = models.TextField(
        verbose_name="Именной сертификат", null=True, blank=True
    )
    why_our_students_elite = models.TextField(
        verbose_name="Почему наши ученики элита", null=True, blank=True
    )
    become_member_link = models.URLField(
        verbose_name="Стать участником курса", null=True, blank=True
    )
    get_consultation_link = models.URLField(
        verbose_name="Получить консультацию", null=True, blank=True
    )

    def __str__(self):
        return self.title

    class Meta:
        db_table = "courses"
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"


class AdditionalField(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="additional_fields",
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    description = RichTextUploadingField(verbose_name="Описание")
    show = models.BooleanField(default=True)
    order = models.PositiveIntegerField(db_index=True)

    def __str__(self):
        return self.title if self.title else str(self.pk)

    class Meta:
        db_table = "course_additional_fields"
        verbose_name = "Дополнительное поле"
        verbose_name_plural = "Дополнительные поля"


class VideoPresentation(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="video_presentations",
    )
    title = models.CharField(verbose_name="Название", max_length=255)
    link = models.URLField(verbose_name="Ссылка на видео")
    show = models.BooleanField(default=True)
    order = models.PositiveIntegerField(db_index=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "course_video_presentations"
        verbose_name = "Видео презентация"
        verbose_name_plural = "Видео презентации"


class ForWhomCourse(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="for_whom_courses",
    )
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=200, verbose_name="Название")
    description = RichTextUploadingField(verbose_name="Описание")
    show = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "for_whom_courses"
        verbose_name = "Для кого курс"
        verbose_name_plural = "Для кого курсы"


class WithinCourse(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="within_courses",
    )
    order = models.PositiveIntegerField(db_index=True)
    description = RichTextUploadingField(verbose_name="Описание")
    show = models.BooleanField(default=True)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "within_courses"
        verbose_name = "В рамках курса"
        verbose_name_plural = "В рамках курсов"


class WhatYouBuy(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="what_you_buys",
    )
    order = models.PositiveIntegerField(db_index=True)
    description = RichTextUploadingField(verbose_name="Описание")
    show = models.BooleanField(default=True)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "what_you_buys"
        verbose_name = "Что вы покупаете"
        verbose_name_plural = "Что вы покупаете"


class PaymentOptionType(models.Model):
    title = models.CharField(max_length=255)
    alias = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "payment_option_types"
        verbose_name = "Тип варианта оплаты"
        verbose_name_plural = "Типы вариантов оплаты"


class PaymentOption(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="payment_options",
    )
    title = models.CharField(max_length=255)
    payment_option_type = models.ForeignKey(
        verbose_name="Тип варианта оплаты",
        to=PaymentOptionType,
        on_delete=models.CASCADE,
        related_name="payment_option_types",
    )
    description = RichTextUploadingField(verbose_name="Описание")
    description_price = RichTextUploadingField(verbose_name="Описание цены")
    full_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Полная стоимость"
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена со скидкой",
    )
    payment_link = models.URLField(null=True, blank=True)
    show = models.BooleanField(default=True)
    order = models.PositiveIntegerField(db_index=True)

    def __str__(self):
        return self.course.title

    class Meta:
        db_table = "payment_options"
        verbose_name = "Вариант оплаты"
        verbose_name_plural = "Варианты оплат"


class QuestionLeft(models.Model):
    course = models.OneToOneField(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="question_lefts",
    )
    description = RichTextUploadingField(verbose_name="Описание")
    show = models.BooleanField(default=True)
    link = models.URLField(verbose_name="Написать в школу")

    def __str__(self):
        return self.description

    class Meta:
        db_table = "question_lefts"
        verbose_name = "Остались вопросы?"
        verbose_name_plural = "Остались вопросы?"


class WhyOurStudentsEliteItem(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="why_our_students_elite_items",
    )
    description = RichTextUploadingField(verbose_name="Описание")
    show = models.BooleanField(default=True)
    order = models.PositiveIntegerField(db_index=True)

    class Meta:
        db_table = "why_our_students_elite_items"
        verbose_name = "Почему наши ученики элита Астрологии?"
        verbose_name_plural = "Почему наши ученики элита Астрологии?"


class Module(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="course_modules",
    )
    title = models.CharField(max_length=200, verbose_name="Название модуля")
    description = RichTextUploadingField(
        verbose_name="Описание", default="", null=True, blank=True
    )
    order = models.PositiveIntegerField(db_index=True)
    updated = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    publish_date = models.DateField(verbose_name="Дата начала", null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "course_modules"
        verbose_name = "Модуль"
        verbose_name_plural = "Модули"


class Lesson(OrderedModel):
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
        related_name="lessons",
        null=True,
        blank=True,
    )
    module = models.ForeignKey(
        to=Module,
        on_delete=models.CASCADE,
        verbose_name="Модуль",
        related_name="module_lessons",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, verbose_name="Название урока")
    description = RichTextUploadingField(
        verbose_name="Описание", default="", null=True, blank=True
    )
    order = models.PositiveIntegerField(db_index=True)
    updated = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    publish_date = models.DateField(verbose_name="Дата начала", null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "lessons"
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"


class Curriculum(models.Model):
    user = models.ForeignKey(
        User, related_name="user_curriculums", on_delete=models.CASCADE
    )
    course = models.ForeignKey(
        Course, related_name="course_curriculums", on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "curriculums"
        verbose_name = "Учебный план"
        verbose_name_plural = "Учебные планы"


class Bonus(models.Model):
    payment_option = models.ForeignKey(
        PaymentOption, related_name="bonuses", on_delete=models.CASCADE
    )
    text = models.TextField()

    def __str__(self):
        return self.text

    class Meta:
        db_table = "bonuses"
        verbose_name = "Бонус"
        verbose_name_plural = "Бонусы"


def upload_to(instance, filename):
    return 'images/alpha/{filename}'.format(filename=filename)


class Tag(models.Model):
    title = models.CharField(verbose_name="Название", max_length=255)
    alias = models.CharField(verbose_name="Псевдоним", max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Тег для курсов"
        verbose_name_plural = "Теги для курсов"


class Feature(models.Model):
    title = models.CharField(verbose_name="Название", max_length=255)
    alias = models.CharField(verbose_name="Псевдоним", max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Особенность курсов"
        verbose_name_plural = "Особенности курсов"


class AdvCourseCard(models.Model):
    title = models.CharField(verbose_name="Название курса", max_length=255)
    price = models.CharField(verbose_name="Цена", max_length=255, null=True, blank=True)
    previous_price = models.CharField(verbose_name="Предыдущая цена", max_length=255, null=True, blank=True)
    description = models.CharField(verbose_name="Описание", max_length=255, null=True, blank=True)
    publish_start = models.DateField(verbose_name="Дата начала", null=True, blank=True)
    show_card = models.BooleanField(default=True)
    course = models.ForeignKey(
        Course, related_name="course_advs", on_delete=models.CASCADE, null=True, blank=True
    )
    link = models.URLField(
        verbose_name="Ссылка курс на сайте", null=True, blank=True
    )
    image = models.ImageField("Фото", storage=MinioBackend(bucket_name='alpha'), upload_to=upload_to)
    banner_type = models.ManyToManyField(
        BannerType,
        related_name="adv_course_cards",
        blank=True
    )
    features = models.ManyToManyField(
        Feature,
        related_name="adv_course_cards",
        blank=True
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="adv_course_cards",
        blank=True
    )
    target_languages = models.ManyToManyField(
        settings.APP_LANGUAGE_MODEL,
        related_name="adv_course_cards",
        blank=False
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Карточка рекламы курса"
        verbose_name_plural = "Карточки рекламы курсов"
