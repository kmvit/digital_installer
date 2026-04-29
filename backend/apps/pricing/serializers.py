from rest_framework import serializers

from .models import PriceList, PriceListItem, WorkType


class WorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkType
        fields = ("id", "price_list", "section", "name", "order")
        read_only_fields = ("id",)


class PriceListSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)
    objects_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PriceList
        fields = (
            "id",
            "title",
            "version",
            "is_active",
            "items_count",
            "objects_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "items_count", "objects_count", "created_at", "updated_at")


class PriceListItemSerializer(serializers.ModelSerializer):
    price_list_title = serializers.CharField(source="price_list.title", read_only=True)
    work_type_name = serializers.CharField(source="work_type.name", read_only=True, default=None)

    class Meta:
        model = PriceListItem
        fields = (
            "id",
            "price_list",
            "price_list_title",
            "work_type",
            "work_type_name",
            "item_number",
            "name",
            "composition",
            "unit",
            "note",
            "base_rate",
            "smr_rate",
            "materials_rate",
            "pir_rate",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "price_list_title", "work_type_name", "created_at", "updated_at")
