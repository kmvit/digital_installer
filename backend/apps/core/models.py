from django.db import models


class SystemSetting(models.Model):
    key = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Ключ",
        help_text="Уникальный ключ настройки, например: workday_start.",
    )
    value = models.TextField(
        blank=True,
        verbose_name="Значение",
        help_text="Текущее значение настройки в строковом виде.",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Описание",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Системная настройка"
        verbose_name_plural = "Системные настройки"
        ordering = ("key",)

    def __str__(self) -> str:
        return self.key
