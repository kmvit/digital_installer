from tempfile import NamedTemporaryFile

from django import forms
from django.contrib import admin, messages
from django.core.management import call_command, CommandError
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .models import PriceList, PriceListItem


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0


class PriceListImportForm(forms.Form):
    file = forms.FileField(label="Excel файл (.xlsx)")
    title = forms.CharField(label="Название базы расценок", max_length=200)
    version = forms.CharField(label="Версия", max_length=50, initial="1.0")
    sheet = forms.CharField(label="Лист (необязательно)", max_length=100, required=False)
    replace = forms.BooleanField(label="Перезаписать существующие позиции", required=False)


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "version", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "version")
    inlines = [PriceListItemInline]
    change_list_template = "admin/pricing/pricelist/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xlsx/",
                self.admin_site.admin_view(self.import_xlsx_view),
                name="pricing_pricelist_import_xlsx",
            ),
        ]
        return custom_urls + urls

    def import_xlsx_view(self, request):
        form = PriceListImportForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            excel_file = form.cleaned_data["file"]
            title = form.cleaned_data["title"]
            version = form.cleaned_data["version"]
            sheet = form.cleaned_data["sheet"] or None
            replace = form.cleaned_data["replace"]

            if not excel_file.name.lower().endswith(".xlsx"):
                form.add_error("file", "Поддерживаются только файлы .xlsx")
            else:
                with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp_file:
                    for chunk in excel_file.chunks():
                        tmp_file.write(chunk)
                    tmp_file.flush()

                    command_kwargs = {
                        "file": tmp_file.name,
                        "title": title,
                        "pricelist_version": version,
                    }
                    if sheet:
                        command_kwargs["sheet"] = sheet
                    if replace:
                        command_kwargs["replace"] = True

                    try:
                        call_command("import_pricelist", **command_kwargs)
                    except CommandError as exc:
                        form.add_error(None, str(exc))
                    else:
                        self.message_user(
                            request,
                            "Импорт расценок завершен успешно.",
                            level=messages.SUCCESS,
                        )
                        changelist_url = reverse("admin:pricing_pricelist_changelist")
                        return HttpResponseRedirect(changelist_url)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Импорт расценок из Excel",
            "form": form,
        }
        return TemplateResponse(request, "admin/pricing/pricelist/import_form.html", context)


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ("id", "item_number", "name", "unit", "base_rate", "price_list")
    list_filter = ("price_list",)
    search_fields = ("item_number", "name")
