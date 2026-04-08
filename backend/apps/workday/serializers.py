from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    CompletedWork,
    EquipmentCheckItem,
    EquipmentChecklist,
    ObjectSession,
    WorkDay,
    WorkDayStatus,
    WorkPhoto,
)


# ---------------------------------------------------------------------------
# Фото работ
# ---------------------------------------------------------------------------

class WorkPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkPhoto
        fields = ("id", "photo", "latitude", "longitude", "captured_at", "created_at")
        read_only_fields = ("id", "created_at")


# ---------------------------------------------------------------------------
# Выполненные работы
# ---------------------------------------------------------------------------

class CompletedWorkSerializer(serializers.ModelSerializer):
    photos = WorkPhotoSerializer(many=True, read_only=True)
    work_name = serializers.CharField(source="price_list_item.name", read_only=True)
    unit = serializers.CharField(source="price_list_item.unit", read_only=True)
    rate = serializers.DecimalField(
        source="price_list_item.base_rate", read_only=True,
        max_digits=14, decimal_places=2,
    )
    total = serializers.SerializerMethodField()
    has_photos = serializers.SerializerMethodField()

    class Meta:
        model = CompletedWork
        fields = (
            "id", "object_session", "price_list_item",
            "work_name", "unit", "rate",
            "volume", "total", "comment",
            "has_photos", "photos",
            "created_by", "created_at",
        )
        read_only_fields = ("id", "created_by", "created_at")

    def get_total(self, obj) -> str:
        if obj.price_list_item and obj.price_list_item.base_rate:
            return str(obj.volume * obj.price_list_item.base_rate)
        return "0"

    def get_has_photos(self, obj) -> bool:
        return obj.photos.exists()


class CompletedWorkWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompletedWork
        fields = ("id", "object_session", "price_list_item", "volume", "comment")
        read_only_fields = ("id", "object_session")


# ---------------------------------------------------------------------------
# Сессии на объектах
# ---------------------------------------------------------------------------

class ObjectSessionSerializer(serializers.ModelSerializer):
    object_name = serializers.CharField(source="project_object.name", read_only=True)
    object_address = serializers.CharField(source="project_object.address", read_only=True)
    completed_works = CompletedWorkSerializer(many=True, read_only=True)
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = ObjectSession
        fields = (
            "id", "workday", "project_object",
            "object_name", "object_address",
            "arrived_at", "arrived_photo",
            "arrived_latitude", "arrived_longitude",
            "departed_at", "departed_photo",
            "departed_latitude", "departed_longitude",
            "duration_minutes",
            "notes", "completed_works", "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_duration_minutes(self, obj) -> int | None:
        if obj.arrived_at and obj.departed_at:
            return int((obj.departed_at - obj.arrived_at).total_seconds() / 60)
        return None


class ObjectSessionListSerializer(serializers.ModelSerializer):
    """Лёгкий сериализатор для списка сессий."""
    object_name = serializers.CharField(source="project_object.name", read_only=True)
    works_count = serializers.SerializerMethodField()

    class Meta:
        model = ObjectSession
        fields = (
            "id", "project_object", "object_name",
            "arrived_at", "departed_at", "works_count",
        )

    def get_works_count(self, obj) -> int:
        return obj.completed_works.count()


# ---------------------------------------------------------------------------
# Позиции чек-листа
# ---------------------------------------------------------------------------

class EquipmentCheckItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentCheckItem
        fields = ("id", "name", "status", "photo", "qr_code", "notes")
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Чек-лист оборудования
# ---------------------------------------------------------------------------

class EquipmentChecklistSerializer(serializers.ModelSerializer):
    items = EquipmentCheckItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default="",
    )

    class Meta:
        model = EquipmentChecklist
        fields = (
            "id", "workday", "checklist_type",
            "created_by", "created_by_name",
            "notes", "items", "created_at",
        )
        read_only_fields = ("id", "created_by", "created_at")


class EquipmentChecklistWriteSerializer(serializers.Serializer):
    """Сериализатор для создания чек-листа с позициями за один запрос."""
    checklist_type = serializers.ChoiceField(choices=["morning", "evening"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = EquipmentCheckItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Чек-лист должен содержать хотя бы одну позицию.")
        return value


# ---------------------------------------------------------------------------
# Рабочий день
# ---------------------------------------------------------------------------

class WorkDayDetailSerializer(serializers.ModelSerializer):
    brigade_name = serializers.CharField(source="brigade.name", read_only=True)
    foreman_name = serializers.CharField(source="foreman.get_full_name", read_only=True)
    sessions = ObjectSessionSerializer(many=True, read_only=True)
    equipment_checklists = EquipmentChecklistSerializer(many=True, read_only=True)
    workers_present_list = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()

    class Meta:
        model = WorkDay
        fields = (
            "id", "brigade", "brigade_name",
            "foreman", "foreman_name", "date",
            "clock_in_at", "clock_in_photo",
            "clock_in_latitude", "clock_in_longitude",
            "clock_out_at", "clock_out_photo",
            "clock_out_latitude", "clock_out_longitude",
            "workers_present", "workers_present_list",
            "status", "pm_comment",
            "approved_by", "approved_at",
            "total_hours",
            "sessions", "equipment_checklists",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "brigade_name", "foreman_name",
            "workers_present_list", "total_hours",
            "sessions", "equipment_checklists",
            "created_at", "updated_at",
        )

    def get_workers_present_list(self, obj) -> list:
        return [
            {"id": u.id, "name": u.get_full_name() or u.username}
            for u in obj.workers_present.all()
        ]

    def get_total_hours(self, obj) -> float | None:
        if obj.clock_in_at and obj.clock_out_at:
            return round((obj.clock_out_at - obj.clock_in_at).total_seconds() / 3600, 2)
        return None


class WorkDayListSerializer(serializers.ModelSerializer):
    brigade_name = serializers.CharField(source="brigade.name", read_only=True)
    foreman_name = serializers.CharField(source="foreman.get_full_name", read_only=True)
    sessions_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkDay
        fields = (
            "id", "brigade", "brigade_name",
            "foreman", "foreman_name", "date",
            "clock_in_at", "clock_out_at",
            "status", "sessions_count",
            "created_at",
        )

    def get_sessions_count(self, obj) -> int:
        return obj.sessions.count()


# ---------------------------------------------------------------------------
# Clock-in / Clock-out
# ---------------------------------------------------------------------------

class ClockInSerializer(serializers.Serializer):
    photo = serializers.ImageField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    workers_present = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list,
    )


class ClockOutSerializer(serializers.Serializer):
    photo = serializers.ImageField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Arrive / Depart
# ---------------------------------------------------------------------------

class ArriveSerializer(serializers.Serializer):
    project_object = serializers.IntegerField()
    photo = serializers.ImageField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


class DepartSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    photo = serializers.ImageField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Приёмка / Отклонение отчёта
# ---------------------------------------------------------------------------

class ApproveRejectSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Саммари дня
# ---------------------------------------------------------------------------

class WorkDaySummarySerializer(serializers.Serializer):
    """Полная сводка за рабочий день."""
    workday_id = serializers.IntegerField()
    date = serializers.DateField()
    brigade = serializers.CharField()
    foreman = serializers.CharField()
    status = serializers.CharField()
    total_hours = serializers.FloatField(allow_null=True)
    sessions = serializers.ListField()
    total_works = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    works_without_photos = serializers.IntegerField()
    equipment_morning = serializers.DictField(allow_null=True)
    equipment_evening = serializers.DictField(allow_null=True)
    equipment_diff = serializers.ListField()
