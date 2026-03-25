from django.contrib import admin

from .models import ObjectDocument, ObjectStage, ProjectObject, Stage


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "order")
    ordering = ("order",)


class ObjectStageInline(admin.TabularInline):
    model = ObjectStage
    extra = 0


class ObjectDocumentInline(admin.TabularInline):
    model = ObjectDocument
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


@admin.register(ProjectObject)
class ProjectObjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "customer", "current_stage", "price_list", "deadline", "is_archived", "updated_at")
    list_filter = ("is_archived", "price_list", "current_stage")
    search_fields = ("name", "address", "customer")
    inlines = [ObjectStageInline, ObjectDocumentInline]


@admin.register(ObjectStage)
class ObjectStageAdmin(admin.ModelAdmin):
    list_display = ("id", "project_object", "stage", "planned_date", "actual_date")
    list_filter = ("stage",)


@admin.register(ObjectDocument)
class ObjectDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "doc_type", "project_object", "uploaded_by", "created_at")
    list_filter = ("doc_type",)
    search_fields = ("title",)
