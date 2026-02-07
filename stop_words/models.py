from django.db import models


class Word(models.Model):
    word = models.CharField("Стоп слово", max_length=255)

    class Meta:
        verbose_name = "Стоп слово"
        verbose_name_plural = "Стоп слова"

    def __str__(self):
        return self.word
