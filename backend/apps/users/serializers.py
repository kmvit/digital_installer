from rest_framework import serializers

from .models import Brigade, User


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "role",
        )


class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "role",
            "is_active",
            "password",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class BrigadeSerializer(serializers.ModelSerializer):
    foreman_username = serializers.CharField(source="foreman.username", read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
        source="members",
        write_only=True,
    )
    member_usernames = serializers.SlugRelatedField(
        source="members",
        many=True,
        read_only=True,
        slug_field="username",
    )

    class Meta:
        model = Brigade
        fields = (
            "id",
            "name",
            "foreman",
            "foreman_username",
            "is_active",
            "member_ids",
            "member_usernames",
        )
