from rest_framework import serializers

from .models import ProjectObject


class ProjectObjectSerializer(serializers.ModelSerializer):
    price_list_title = serializers.CharField(source="price_list.title", read_only=True)

    class Meta:
        model = ProjectObject
        fields = ("id", "name", "price_list", "price_list_title", "created_at", "updated_at")
        read_only_fields = ("id", "price_list_title", "created_at", "updated_at")
