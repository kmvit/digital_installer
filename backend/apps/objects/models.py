from django.conf import settings
from django.db import models


class DocumentType(models.TextChoices):
    RD = "rd", "Рабочая документация (РД)"
    PROJECT = "project", "Проект"
    ACT = "act", "Акт"
    SCHEME = "scheme", "Схема"
    OTHER = "other", "Прочее"


class Stage(models.Model):
    """Справочник стадий — создаётся один раз, переиспользуется для всех объектов."""

    name = models.CharField(max_length=128, unique=True, verbose_name="Название")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")

    class Meta:
        db_table = "objects_stage"
        verbose_name = "Стадия"
        verbose_name_plural = "Стадии"
        ordering = ("order",)

    def __str__(self) -> str:
        return self.name


class ProjectObject(models.Model):
    """
    objects (id, name, address, lat, lng, customer, stage_id, price_list_id, attrs{})
    """

    name = models.CharField(max_length=255, unique=True, verbose_name="Название")
    address = models.TextField(blank=True, verbose_name="Адрес")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Широта",
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Долгота",
    )
    customer = models.CharField(max_length=255, blank=True, verbose_name="Заказчик")

    current_stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
        verbose_name="Текущая стадия",
    )

    price_list = models.ForeignKey(
        "pricing.PriceList",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="objects",
        verbose_name="База расценок",
    )

    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="managed_objects",
        verbose_name="Руководитель проекта",
    )
    brigade = models.ForeignKey(
        "users.Brigade",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="project_objects",
        verbose_name="Прикреплённая бригада",
    )
    deadline = models.DateField(null=True, blank=True, verbose_name="Дэдлайн")

    attrs = models.JSONField(default=dict, blank=True, verbose_name="Доп. атрибуты")

    is_archived = models.BooleanField(default=False, db_index=True, verbose_name="В архиве")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        db_table = "core_projectobject"
        verbose_name = "Объект"
        verbose_name_plural = "Объекты"
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return self.name


class ObjectStage(models.Model):
    """Привязка стадии к объекту с плановой и фактической датой."""

    project_object = models.ForeignKey(
        ProjectObject,
        on_delete=models.CASCADE,
        related_name="object_stages",
        verbose_name="Объект",
    )
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name="object_stages",
        verbose_name="Стадия",
    )
    planned_date = models.DateField(null=True, blank=True, verbose_name="Плановая дата")
    actual_date = models.DateField(null=True, blank=True, verbose_name="Фактическая дата")

    class Meta:
        db_table = "objects_objectstage"
        verbose_name = "Стадия объекта"
        verbose_name_plural = "Стадии объектов"
        ordering = ("stage__order",)
        unique_together = ("project_object", "stage")

    def __str__(self) -> str:
        return f"{self.project_object} → {self.stage.name}"


class ObjectDocument(models.Model):
    """Документ (РД, акт, схема и пр.), прикреплённый к объекту."""

    project_object = models.ForeignKey(
        ProjectObject,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Объект",
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    doc_type = models.CharField(
        max_length=32,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        verbose_name="Тип документа",
    )
    file = models.FileField(upload_to="objects/documents/%Y/%m/", verbose_name="Файл")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="uploaded_documents",
        verbose_name="Загрузил",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Загружен")

    class Meta:
        db_table = "objects_objectdocument"
        verbose_name = "Документ объекта"
        verbose_name_plural = "Документы объектов"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.title} ({self.project_object})"
