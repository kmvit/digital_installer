from tempfile import NamedTemporaryFile

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .management.commands.import_objects import import_objects_from_file
from .models import ObjectDocument, ObjectStage, ProjectObject, Stage


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
    change_list_template = "admin/objects/projectobject/change_list.html"

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
                        f"Импорт завершён: создано {result['created']}, пропущено {result['skipped']}.",
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
