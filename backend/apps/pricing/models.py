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
    item_number = models.CharField(max_length=64, blank=True, verbose_name="№ п/п")
    name = models.TextField(verbose_name="Наименование работ")
    composition = models.TextField(blank=True, verbose_name="Состав работ")
    unit = models.CharField(max_length=100, blank=True, verbose_name="Единица измерения")
    note = models.TextField(blank=True, verbose_name="Примечание")
    base_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Удельная стоимость за единицу без НДС, руб.",
    )
    smr_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="в том числе стоимость СМР (работ), руб.",
    )
    materials_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="в том числе стоимость кабеля, материалов, руб.",
    )
    pir_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="в том числе стоимость ПИР, руб.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        db_table = "core_pricelistitem"
        verbose_name = "Позиция расценки"
        verbose_name_plural = "Позиции расценок"
        ordering = ("item_number", "name")

    def __str__(self) -> str:
        return self.name
