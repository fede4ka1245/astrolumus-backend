from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

HOURS = tuple(((str(m), str(m)) for m in range(-13, 14)))
MINUTES = tuple(
    (
        (
            str(m) if len(str(m)) > 1 else f"0{str(m)}",
            str(m) if len(str(m)) > 1 else f"0{str(m)}",
        )
        for m in range(0, 60)
    )
)


class HoroscopeCache(models.Model):
    latitude = models.CharField(max_length=255)
    longitude = models.CharField(max_length=255)
    dt = models.DateTimeField()
    data = models.JSONField(default=dict, editable=True)
    tz_hour = models.CharField(
        choices=HOURS, max_length=5
    )
    tz_minutes = models.CharField(
        choices=MINUTES, max_length=5
    )
    settings = models.CharField(max_length=500)

    class Meta:
        # unique_together = [["latitude", "longitude", "dt", "tz_hour", "tz_minutes"]]
        verbose_name = "Гороскоп"
        verbose_name_plural = "Гороскопы"


class MyHoroscope(models.Model):
    name = models.CharField(default="", blank=True, max_length=255)
    city = models.CharField(default="", blank=True, max_length=255)
    horoscope = models.ForeignKey(HoroscopeCache, related_name="my_horoscopes", on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name="my_horoscopes", on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.user.email)

    class Meta:
        unique_together = [["horoscope", "user"]]
        verbose_name = "Мой гороскоп"
        verbose_name_plural = "Мои гороскопы"


# old models remove TODO
class Horoscope(models.Model):
    data_in = models.TextField()
    data_type = models.CharField(max_length=255)
    data_out = models.JSONField(default=dict, editable=False)

    def __str__(self):
        return self.data_in

    class Meta:
        db_table = "horoscopes"
        verbose_name = "Гороскоп"
        verbose_name_plural = "Гороскопы"


class FullHoroscope(models.Model):
    horoscopes = models.ManyToManyField(to=Horoscope, related_name="horoscope_items", )
    user = models.ForeignKey(
        User, related_name="user_full_horoscopes", on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.user.email)

    class Meta:
        db_table = "full_horoscopes"
        verbose_name = "Полный гороскоп"
        verbose_name_plural = "Полные гороскопы"
