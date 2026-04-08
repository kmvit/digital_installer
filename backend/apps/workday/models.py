from django.conf import settings
from django.db import models


class WorkDayStatus(models.TextChoices):
    OPEN = "open", "Открыт"
    CLOSED = "closed", "Закрыт"
    APPROVED = "approved", "Принят"
    REJECTED = "rejected", "Отклонён"


class ChecklistType(models.TextChoices):
    MORNING = "morning", "Утренний (выдача)"
    EVENING = "evening", "Вечерний (возврат)"


class EquipmentItemStatus(models.TextChoices):
    OK = "ok", "В наличии"
    MISSING = "missing", "Отсутствует"
    DAMAGED = "damaged", "Повреждён"


# ---------------------------------------------------------------------------
# Рабочий день бригады
# ---------------------------------------------------------------------------

class WorkDay(models.Model):
    """Рабочий день бригады: от clock-in до clock-out."""

    brigade = models.ForeignKey(
        "users.Brigade",
        on_delete=models.CASCADE,
        related_name="workdays",
        verbose_name="Бригада",
    )
    foreman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workdays_as_foreman",
        verbose_name="Мастер (бригадир)",
    )
    date = models.DateField(verbose_name="Дата")

    # --- Clock-in ---
    clock_in_at = models.DateTimeField(verbose_name="Время начала смены")
    clock_in_photo = models.ImageField(
        upload_to="workday/clock_in/%Y/%m/%d/", verbose_name="Фото начала смены",
    )
    clock_in_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS широта (начало)",
    )
    clock_in_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS долгота (начало)",
    )

    # --- Clock-out ---
    clock_out_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Время конца смены",
    )
    clock_out_photo = models.ImageField(
        upload_to="workday/clock_out/%Y/%m/%d/", blank=True, verbose_name="Фото конца смены",
    )
    clock_out_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS широта (конец)",
    )
    clock_out_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS долгота (конец)",
    )

    # --- Присутствие ---
    workers_present = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="workday_presences",
        verbose_name="Присутствующие работники",
    )

    # --- Статус и приёмка ---
    status = models.CharField(
        max_length=16,
        choices=WorkDayStatus.choices,
        default=WorkDayStatus.OPEN,
        db_index=True,
        verbose_name="Статус",
    )
    pm_comment = models.TextField(blank=True, verbose_name="Комментарий РП")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_workdays",
        verbose_name="Принял",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата приёмки")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        db_table = "workday_workday"
        verbose_name = "Рабочий день"
        verbose_name_plural = "Рабочие дни"
        ordering = ("-date", "-clock_in_at")

    def __str__(self) -> str:
        return f"{self.brigade} — {self.date}"


# ---------------------------------------------------------------------------
# Сессия работы на объекте
# ---------------------------------------------------------------------------

class ObjectSession(models.Model):
    """Сессия работы бригады на конкретном объекте в рамках рабочего дня."""

    workday = models.ForeignKey(
        WorkDay,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Рабочий день",
    )
    project_object = models.ForeignKey(
        "objects.ProjectObject",
        on_delete=models.CASCADE,
        related_name="work_sessions",
        verbose_name="Объект",
    )

    # --- Прибытие ---
    arrived_at = models.DateTimeField(verbose_name="Время прибытия")
    arrived_photo = models.ImageField(
        upload_to="workday/arrive/%Y/%m/%d/", verbose_name="Фото прибытия",
    )
    arrived_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS широта (прибытие)",
    )
    arrived_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS долгота (прибытие)",
    )

    # --- Убытие ---
    departed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Время убытия",
    )
    departed_photo = models.ImageField(
        upload_to="workday/depart/%Y/%m/%d/", blank=True, verbose_name="Фото убытия",
    )
    departed_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS широта (убытие)",
    )
    departed_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS долгота (убытие)",
    )

    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        db_table = "workday_objectsession"
        verbose_name = "Сессия на объекте"
        verbose_name_plural = "Сессии на объектах"
        ordering = ("arrived_at",)

    def __str__(self) -> str:
        return f"{self.project_object} ({self.arrived_at:%H:%M})"


# ---------------------------------------------------------------------------
# Выполненная работа
# ---------------------------------------------------------------------------

class CompletedWork(models.Model):
    """Зафиксированная выполненная работа в рамках сессии на объекте."""

    object_session = models.ForeignKey(
        ObjectSession,
        on_delete=models.CASCADE,
        related_name="completed_works",
        verbose_name="Сессия",
    )
    price_list_item = models.ForeignKey(
        "pricing.PriceListItem",
        on_delete=models.CASCADE,
        related_name="completed_works",
        verbose_name="Вид работы",
    )
    volume = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="Объём",
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="completed_works",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        db_table = "workday_completedwork"
        verbose_name = "Выполненная работа"
        verbose_name_plural = "Выполненные работы"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.price_list_item.name} × {self.volume}"


# ---------------------------------------------------------------------------
# Фото к выполненной работе
# ---------------------------------------------------------------------------

class WorkPhoto(models.Model):
    """Фотография, привязанная к выполненной работе."""

    completed_work = models.ForeignKey(
        CompletedWork,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Работа",
    )
    photo = models.ImageField(
        upload_to="workday/work_photos/%Y/%m/%d/", verbose_name="Фото",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS широта",
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS долгота",
    )
    captured_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Время съёмки",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Загружено")

    class Meta:
        db_table = "workday_workphoto"
        verbose_name = "Фото работы"
        verbose_name_plural = "Фото работ"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"Фото #{self.pk} к {self.completed_work}"


# ---------------------------------------------------------------------------
# Чек-лист оборудования
# ---------------------------------------------------------------------------

class EquipmentChecklist(models.Model):
    """Чек-лист оборудования (утренний — выдача, вечерний — возврат)."""

    workday = models.ForeignKey(
        WorkDay,
        on_delete=models.CASCADE,
        related_name="equipment_checklists",
        verbose_name="Рабочий день",
    )
    checklist_type = models.CharField(
        max_length=16,
        choices=ChecklistType.choices,
        verbose_name="Тип чек-листа",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="equipment_checklists",
        verbose_name="Заполнил",
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        db_table = "workday_equipmentchecklist"
        verbose_name = "Чек-лист оборудования"
        verbose_name_plural = "Чек-листы оборудования"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.get_checklist_type_display()} — {self.workday}"


# ---------------------------------------------------------------------------
# Позиция чек-листа
# ---------------------------------------------------------------------------

class EquipmentCheckItem(models.Model):
    """Одна позиция (единица оборудования) в чек-листе."""

    checklist = models.ForeignKey(
        EquipmentChecklist,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Чек-лист",
    )
    name = models.CharField(max_length=255, verbose_name="Название оборудования")
    status = models.CharField(
        max_length=16,
        choices=EquipmentItemStatus.choices,
        default=EquipmentItemStatus.OK,
        verbose_name="Статус",
    )
    photo = models.ImageField(
        upload_to="workday/equipment/%Y/%m/%d/", blank=True, verbose_name="Фото",
    )
    qr_code = models.CharField(
        max_length=255, blank=True, verbose_name="QR-код",
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")

    class Meta:
        db_table = "workday_equipmentcheckitem"
        verbose_name = "Позиция чек-листа"
        verbose_name_plural = "Позиции чек-листа"

    def __str__(self) -> str:
        return f"{self.name} — {self.get_status_display()}"
