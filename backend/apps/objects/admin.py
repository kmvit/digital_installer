from tempfile import NamedTemporaryFile

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .management.commands.import_objects import import_objects_from_file
from .models import City, ObjectDocument, ObjectStage, ObjectWorkPlan, ProjectObject, Stage


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


class ObjectImportForm(forms.Form):
    file = forms.FileField(label="Excel файл (.xlsx)")
    sheet = forms.CharField(label="Лист (необязательно)", max_length=100, required=False)


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "order")
    ordering = ("order",)


class ObjectStageInline(admin.TabularInline):
    model = ObjectStage
    extra = 0


class ObjectWorkPlanInline(admin.TabularInline):
    model = ObjectWorkPlan
    extra = 0
    autocomplete_fields = ("work_type",)
    fields = ("work_type", "planned_volume", "planned_start", "planned_end", "notes")


class ObjectDocumentInline(admin.TabularInline):
    model = ObjectDocument
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


class ProjectObjectForm(forms.ModelForm):
    class Meta:
        model = ProjectObject
        fields = "__all__"
        widgets = {
            "geofence_polygon": forms.Textarea(attrs={
                "rows": 3,
                "style": "width:100%; font-family:monospace; font-size:12px;",
            }),
        }


@admin.register(ProjectObject)
class ProjectObjectAdmin(admin.ModelAdmin):
    form = ProjectObjectForm
    list_display = (
        "id", "name", "city", "customer",
        "decision_status", "construction_status", "materials_status", "pir_status", "as_built_status",
        "current_stage", "deadline", "geofence_status", "is_archived", "updated_at",
    )
    list_filter = (
        "is_archived", "current_stage", "city",
        "decision_status", "construction_status", "materials_status", "pir_status", "as_built_status",
    )
    search_fields = ("name", "address", "customer", "city__name")
    filter_horizontal = ("available_work_types",)
    inlines = [ObjectWorkPlanInline, ObjectStageInline, ObjectDocumentInline]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "available_work_types":
            from apps.pricing.models import WorkType
            kwargs["queryset"] = WorkType.objects.select_related("price_list")
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    change_list_template = "admin/objects/projectobject/change_list.html"
    change_form_template = "admin/objects/projectobject/change_form.html"

    @admin.display(description="Геозона")
    def geofence_status(self, obj):
        if obj.geofence_polygon and len(obj.geofence_polygon) > 0:
            return f"Полигон ({len(obj.geofence_polygon)} точек)"
        if obj.presence_radius:
            return f"Радиус {obj.presence_radius} м"
        return "-"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xlsx/",
                self.admin_site.admin_view(self.import_xlsx_view),
                name="objects_projectobject_import_xlsx",
            ),
        ]
        return custom_urls + urls

    def import_xlsx_view(self, request):
        form = ObjectImportForm(request.POST or None, request.FILES or None)
        result = None

        if request.method == "POST" and form.is_valid():
            excel_file = form.cleaned_data["file"]
            sheet = form.cleaned_data["sheet"] or None

            if not excel_file.name.lower().endswith(".xlsx"):
                form.add_error("file", "Поддерживаются только файлы .xlsx")
            else:
                try:
                    result = import_objects_from_file(excel_file, sheet=sheet)
                except Exception as exc:
                    form.add_error(None, str(exc))
                else:
                    self.message_user(
                        request,
                        f"Импорт завершён: создано {result['created']}, обновлено {result['updated']}, пропущено {result['skipped']}.",
                        level=messages.SUCCESS,
                    )
                    changelist_url = reverse("admin:objects_projectobject_changelist")
                    return HttpResponseRedirect(changelist_url)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Импорт объектов из Excel",
            "form": form,
            "result": result,
        }
        return TemplateResponse(request, "admin/objects/projectobject/import_form.html", context)


@admin.register(ObjectStage)
class ObjectStageAdmin(admin.ModelAdmin):
    list_display = ("id", "project_object", "stage", "planned_date", "actual_date")
    list_filter = ("stage",)


@admin.register(ObjectDocument)
class ObjectDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "doc_type", "project_object", "uploaded_by", "created_at")
    list_filter = ("doc_type",)
    search_fields = ("title",)
