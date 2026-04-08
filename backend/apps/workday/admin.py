from django.contrib import admin

from .models import (
    CompletedWork,
    EquipmentCheckItem,
    EquipmentChecklist,
    ObjectSession,
    WorkDay,
    WorkPhoto,
)


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class ObjectSessionInline(admin.TabularInline):
    model = ObjectSession
    extra = 0
    readonly_fields = ("arrived_at", "departed_at", "created_at")
    fields = (
        "project_object", "arrived_at", "arrived_photo",
        "departed_at", "departed_photo", "notes",
    )


class EquipmentChecklistInline(admin.TabularInline):
    model = EquipmentChecklist
    extra = 0
    readonly_fields = ("created_by", "created_at")
    fields = ("checklist_type", "created_by", "notes", "created_at")


class CompletedWorkInline(admin.TabularInline):
    model = CompletedWork
    extra = 0
    readonly_fields = ("created_by", "created_at")
    fields = ("price_list_item", "volume", "comment", "created_by", "created_at")


class WorkPhotoInline(admin.TabularInline):
    model = WorkPhoto
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("photo", "latitude", "longitude", "captured_at", "created_at")


class EquipmentCheckItemInline(admin.TabularInline):
    model = EquipmentCheckItem
    extra = 0
    fields = ("name", "status", "photo", "qr_code", "notes")


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------

@admin.register(WorkDay)
class WorkDayAdmin(admin.ModelAdmin):
    list_display = (
        "id", "date", "brigade", "foreman",
        "clock_in_at", "clock_out_at",
        "status", "approved_by", "updated_at",
    )
    list_filter = ("status", "date", "brigade")
    search_fields = ("brigade__name", "foreman__username", "foreman__first_name", "foreman__last_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ObjectSessionInline, EquipmentChecklistInline]
    filter_horizontal = ("workers_present",)


@admin.register(ObjectSession)
class ObjectSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "workday", "project_object", "arrived_at", "departed_at")
    list_filter = ("workday__date",)
    search_fields = ("project_object__name",)
    inlines = [CompletedWorkInline]


@admin.register(CompletedWork)
class CompletedWorkAdmin(admin.ModelAdmin):
    list_display = ("id", "object_session", "price_list_item", "volume", "created_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("price_list_item__name",)
    inlines = [WorkPhotoInline]


@admin.register(EquipmentChecklist)
class EquipmentChecklistAdmin(admin.ModelAdmin):
    list_display = ("id", "workday", "checklist_type", "created_by", "created_at")
    list_filter = ("checklist_type", "created_at")
    inlines = [EquipmentCheckItemInline]
