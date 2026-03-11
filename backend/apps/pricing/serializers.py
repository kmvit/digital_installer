from rest_framework import serializers

from .models import PriceList, PriceListItem


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

    class Meta:
        model = PriceListItem
        fields = (
            "id",
            "price_list",
            "price_list_title",
            "section",
            "name",
            "unit",
            "rate",
            "short_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "price_list_title", "created_at", "updated_at")
