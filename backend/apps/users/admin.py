from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("phone", "status", "roles")}),
    )
    list_display = ("id", "username", "email", "status", "is_active", "is_staff")
    list_filter = ("status", "roles", "is_active", "is_staff")
    filter_horizontal = ("groups", "user_permissions", "roles")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_system")
    list_filter = ("is_system",)
    search_fields = ("code", "name")
