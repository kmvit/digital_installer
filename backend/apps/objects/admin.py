from django.contrib import admin

from .models import ProjectObject


@admin.register(ProjectObject)
class ProjectObjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price_list", "updated_at")
    list_filter = ("price_list",)
    search_fields = ("name",)
