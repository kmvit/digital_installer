from django.db import models


class PriceList(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название базы расценок")
    version = models.CharField(max_length=50, default="1.0", verbose_name="Версия")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        db_table = "core_pricelist"
        verbose_name = "База расценок"
        verbose_name_plural = "Базы расценок"
        ordering = ("-updated_at",)
        unique_together = ("title", "version")

    def __str__(self) -> str:
        return f"{self.title} v{self.version}"


class PriceListItem(models.Model):
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="База расценок",
    )
    section = models.CharField(max_length=120, blank=True, verbose_name="Раздел")
    name = models.CharField(max_length=255, verbose_name="Наименование работы")
    unit = models.CharField(max_length=30, verbose_name="Единица измерения")
    rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Расценка, руб.")
    short_description = models.TextField(blank=True, verbose_name="Краткое содержание работ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        db_table = "core_pricelistitem"
        verbose_name = "Позиция расценки"
        verbose_name_plural = "Позиции расценок"
        ordering = ("section", "name")

    def __str__(self) -> str:
        return self.name
