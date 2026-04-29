from django.conf import settings
from django.db import models


class DocumentType(models.TextChoices):
    RD = "rd", "Рабочая документация (РД)"
    PROJECT = "project", "Проект"
    ACT = "act", "Акт"
    SCHEME = "scheme", "Схема"
    OTHER = "other", "Прочее"


class City(models.Model):
    """Справочник городов."""

    name = models.CharField(max_length=128, unique=True, verbose_name="Название")

    class Meta:
        db_table = "objects_city"
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


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


class DecisionStatus(models.TextChoices):
    ANALYSIS = "analysis", "Анализ"
    IN_PROGRESS = "in_progress", "Строим"
    REJECTED = "rejected", "Отказ"
    TRANSFERRED_TO_SP = "transferred_to_sp", "Передан СП"
    ARCHIVE_ANALYSIS = "archive_analysis", "Архив анализ"


class ConstructionStatus(models.TextChoices):
    SURVEY = "survey", "Обследовать"
    SELECT_SOFTWARE = "select_software", "Выбрать ПО"
    BUILD = "build", "Строить"
    COMPLETED = "completed", "Завершен"
    COMPLETED_TODO = "completed_todo", "Завершен (доделать)"
    COMPLETED_PAID = "completed_paid", "Завершен оплачен"


class MaterialsStatus(models.TextChoices):
    ORDER = "order", "Заказать"
    ORDERED = "ordered", "Заказаны"
    ARRIVED = "arrived", "Пришли"
    SP = "sp", "СП"


class PirStatus(models.TextChoices):
    DEVELOP = "develop", "Разработать"
    AGREED_RTK = "agreed_rtk", "Согл. с РТК"
    AGREED_SERVICES = "agreed_services", "Согл. со службами"
    SUBMIT_PIR = "submit_pir", "Сдать ПИР"
    COMPLETED = "completed", "Завершен"
    NOT_TAKEN = "not_taken", "Не брали"
    SP = "sp", "СП"


class AsBuiltStatus(models.TextChoices):
    ASSIGN = "assign", "Назначить"
    IN_DEVELOPMENT = "in_development", "Разработка"
    SUBMITTED_MP = "submitted_mp", "Сдан МП"
    CHECK_RTK = "check_rtk", "Проверка РТК"
    REWORK_PP = "rework_pp", "Доработка ПП"
    SUBMITTED_PP = "submitted_pp", "Сдан ПП"
    NOT_REQUIRED = "not_required", "Не требуется"


class ProjectObject(models.Model):
    """
    objects (id, name, address, lat, lng, customer, stage_id, price_list_id, attrs{})
    """

    name = models.CharField(max_length=255, verbose_name="Название")
    city = models.ForeignKey(
        "objects.City",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="project_objects",
        verbose_name="Город",
    )
    address = models.TextField(blank=True, verbose_name="Адрес")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Широта",
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Долгота",
    )
    geofence_polygon = models.JSONField(
        default=list, blank=True, verbose_name="Геозона (полигон)",
        help_text="Массив координат [[lat, lng], ...] для определения границ объекта",
    )
    presence_radius = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Радиус присутствия (м)",
        help_text="Радиус в метрах для определения присутствия бригады на объекте",
    )
    customer = models.CharField(max_length=255, blank=True, verbose_name="Заказчик")
    decision_status = models.CharField(
        max_length=32,
        choices=DecisionStatus.choices,
        blank=True,
        db_index=True,
        verbose_name="Решение",
    )
    construction_status = models.CharField(
        max_length=32,
        choices=ConstructionStatus.choices,
        blank=True,
        db_index=True,
        verbose_name="Статус стройки",
    )
    materials_status = models.CharField(
        max_length=32,
        choices=MaterialsStatus.choices,
        blank=True,
        db_index=True,
        verbose_name="Статус материалы",
    )
    pir_status = models.CharField(
        max_length=32,
        choices=PirStatus.choices,
        blank=True,
        db_index=True,
        verbose_name="Статус ПИР",
    )
    as_built_status = models.CharField(
        max_length=32,
        choices=AsBuiltStatus.choices,
        blank=True,
        db_index=True,
        verbose_name="Статус ИД",
    )

    current_stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
        verbose_name="Текущая стадия",
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

    notes = models.TextField(blank=True, verbose_name="Примечания")
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


class ObjectWorkPlan(models.Model):
    """Плановый объём работ по виду работ для конкретного объекта.

    Используется для расчёта прогресса (план/факт/прогноз) по принципам
    «Управления заработанной стоимостью» (Earned Value). Может расширяться
    дополнительными атрибутами (стоимость, ответственный, статус и т.д.)
    """

    project_object = models.ForeignKey(
        ProjectObject,
        on_delete=models.CASCADE,
        related_name="work_plans",
        verbose_name="Объект",
    )
    work_type = models.ForeignKey(
        "pricing.WorkType",
        on_delete=models.PROTECT,
        related_name="object_plans",
        verbose_name="Вид работ",
    )
    planned_volume = models.DecimalField(
        max_digits=14, decimal_places=3, default=0, verbose_name="Плановый объём",
        help_text="Можно оставить 0, если просто нужно разрешить вид работ без планирования объёма.",
    )
    planned_start = models.DateField(null=True, blank=True, verbose_name="План: старт")
    planned_end = models.DateField(null=True, blank=True, verbose_name="План: завершение")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        db_table = "objects_objectworkplan"
        verbose_name = "Плановый объём работ"
        verbose_name_plural = "Плановые объёмы работ"
        unique_together = ("project_object", "work_type")
        ordering = ("planned_start", "id")

    def __str__(self) -> str:
        return f"{self.project_object} → {self.work_type}: {self.planned_volume}"


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
