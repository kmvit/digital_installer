from rest_framework import serializers

from .models import ObjectDocument, ObjectStage, ProjectObject, Stage


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
    price_list_title = serializers.CharField(source="price_list.title", read_only=True, default=None)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True, default=None)

    class Meta:
        model = ProjectObject
        fields = (
            "id", "name", "address", "customer",
            "current_stage", "current_stage_name",
            "price_list", "price_list_title",
            "deadline", "is_archived",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# Объект — детальный
# ---------------------------------------------------------------------------

class ProjectObjectDetailSerializer(serializers.ModelSerializer):
    price_list_title = serializers.CharField(source="price_list.title", read_only=True, default=None)
    project_manager_name = serializers.CharField(source="project_manager.get_full_name", read_only=True, default=None)
    brigade_name = serializers.CharField(source="brigade.name", read_only=True, default=None)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True, default=None)
    object_stages = ObjectStageSerializer(many=True, read_only=True)
    documents = ObjectDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectObject
        fields = (
            "id",
            "name", "address", "latitude", "longitude",
            "customer",
            "current_stage", "current_stage_name",
            "price_list", "price_list_title",
            "project_manager", "project_manager_name",
            "brigade", "brigade_name",
            "deadline", "attrs", "is_archived",
            "object_stages", "documents",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "price_list_title", "project_manager_name",
            "brigade_name", "current_stage_name",
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
            "name", "address", "latitude", "longitude",
            "customer", "current_stage",
            "price_list",
            "project_manager", "brigade",
            "deadline", "attrs", "is_archived",
        )
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Смена стадии
# ---------------------------------------------------------------------------

class ChangeStageSerializer(serializers.Serializer):
    stage_id = serializers.IntegerField(help_text="ID стадии из справочника Stage")
    actual_date = serializers.DateField(
        required=False, allow_null=True,
        help_text="Фактическая дата завершения предыдущей стадии (по умолчанию — сегодня)",
    )
