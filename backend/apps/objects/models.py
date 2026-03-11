from django.db import models


class ProjectObject(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название объекта")
    price_list = models.ForeignKey(
        "pricing.PriceList",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="objects",
        verbose_name="База расценок",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        db_table = "core_projectobject"
        verbose_name = "Объект"
        verbose_name_plural = "Объекты"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
