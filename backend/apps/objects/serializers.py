from rest_framework import serializers

from .models import City, ObjectDocument, ObjectStage, ProjectObject, Stage


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name")


# ---------------------------------------------------------------------------
# Справочник стадий
# ---------------------------------------------------------------------------

class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ("id", "name", "order")


# ---------------------------------------------------------------------------
# Привязка стадии к объекту
# ---------------------------------------------------------------------------

class ObjectStageSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)

    class Meta:
        model = ObjectStage
        fields = ("id", "stage", "stage_name", "planned_date", "actual_date")
        read_only_fields = ("id", "stage_name")


# ---------------------------------------------------------------------------
# Документы
# ---------------------------------------------------------------------------

class ObjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.get_full_name", read_only=True, default="",
    )

    class Meta:
        model = ObjectDocument
        fields = ("id", "title", "doc_type", "file", "uploaded_by", "uploaded_by_name", "created_at")
        read_only_fields = ("id", "uploaded_by", "uploaded_by_name", "created_at")


# ---------------------------------------------------------------------------
# Объект — список
# ---------------------------------------------------------------------------

class ProjectObjectListSerializer(serializers.ModelSerializer):
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True, default=None)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)
    decision_status_display = serializers.CharField(source="get_decision_status_display", read_only=True)
    construction_status_display = serializers.CharField(source="get_construction_status_display", read_only=True)
    materials_status_display = serializers.CharField(source="get_materials_status_display", read_only=True)
    pir_status_display = serializers.CharField(source="get_pir_status_display", read_only=True)
    as_built_status_display = serializers.CharField(source="get_as_built_status_display", read_only=True)

    class Meta:
        model = ProjectObject
        fields = (
            "id", "name", "city", "city_name", "address", "customer",
            "decision_status", "decision_status_display",
            "construction_status", "construction_status_display",
            "materials_status", "materials_status_display",
            "pir_status", "pir_status_display",
            "as_built_status", "as_built_status_display",
            "current_stage", "current_stage_name",
            "deadline", "is_archived",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# Объект — детальный
# ---------------------------------------------------------------------------

class ProjectObjectDetailSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)
    project_manager_name = serializers.CharField(source="project_manager.get_full_name", read_only=True, default=None)
    brigade_name = serializers.CharField(source="brigade.name", read_only=True, default=None)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True, default=None)
    decision_status_display = serializers.CharField(source="get_decision_status_display", read_only=True)
    construction_status_display = serializers.CharField(source="get_construction_status_display", read_only=True)
    materials_status_display = serializers.CharField(source="get_materials_status_display", read_only=True)
    pir_status_display = serializers.CharField(source="get_pir_status_display", read_only=True)
    as_built_status_display = serializers.CharField(source="get_as_built_status_display", read_only=True)
    object_stages = ObjectStageSerializer(many=True, read_only=True)
    documents = ObjectDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectObject
        fields = (
            "id",
            "name", "city", "city_name", "address", "latitude", "longitude",
            "geofence_polygon", "presence_radius",
            "customer",
            "decision_status", "decision_status_display",
            "construction_status", "construction_status_display",
            "materials_status", "materials_status_display",
            "pir_status", "pir_status_display",
            "as_built_status", "as_built_status_display",
            "current_stage", "current_stage_name",
            "available_work_types",
            "project_manager", "project_manager_name",
            "brigade", "brigade_name",
            "deadline", "notes", "attrs", "is_archived",
            "object_stages", "documents",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "project_manager_name",
            "brigade_name", "current_stage_name",
            "decision_status_display",
            "construction_status_display",
            "materials_status_display",
            "pir_status_display",
            "as_built_status_display",
            "object_stages", "documents",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# Объект — запись
# ---------------------------------------------------------------------------

class ProjectObjectWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectObject
        fields = (
            "id",
            "name", "city", "address", "latitude", "longitude",
            "geofence_polygon", "presence_radius",
            "customer",
            "decision_status",
            "construction_status",
            "materials_status",
            "pir_status",
            "as_built_status",
            "current_stage",
            "available_work_types",
            "project_manager", "brigade",
            "deadline", "notes", "attrs", "is_archived",
        )
        read_only_fields = ("id",)

    def validate_geofence_polygon(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Должен быть массивом координат [[lat, lng], ...]")
        for i, point in enumerate(value):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise serializers.ValidationError(f"Точка {i}: должна быть парой [lat, lng]")
            try:
                lat, lng = float(point[0]), float(point[1])
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"Точка {i}: координаты должны быть числами")
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise serializers.ValidationError(f"Точка {i}: координаты вне допустимого диапазона")
        return value


# ---------------------------------------------------------------------------
# Смена стадии
# ---------------------------------------------------------------------------

class ChangeStageSerializer(serializers.Serializer):
    stage_id = serializers.IntegerField(help_text="ID стадии из справочника Stage")
    actual_date = serializers.DateField(
        required=False, allow_null=True,
        help_text="Фактическая дата завершения предыдущей стадии (по умолчанию — сегодня)",
    )
