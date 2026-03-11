from django.contrib import admin

from .models import PriceList, PriceListItem


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "version", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "version")
    inlines = [PriceListItemInline]


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "section", "unit", "rate", "price_list")
    list_filter = ("price_list", "section")
    search_fields = ("name", "section")
