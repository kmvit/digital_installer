from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Brigade, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("phone", "status", "role")}),
    )
    list_display = ("id", "username", "email", "role", "status", "is_active", "is_staff")
    list_filter = ("role", "status", "is_active", "is_staff")
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Brigade)
class BrigadeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "foreman", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    filter_horizontal = ("members",)
