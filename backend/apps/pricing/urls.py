from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PriceListExportStubView,
    PriceListImportStubView,
    PriceListItemViewSet,
    PriceListViewSet,
)

router = DefaultRouter()
router.register(r"pricelists", PriceListViewSet, basename="admin-pricelists")
router.register(r"pricelist-items", PriceListItemViewSet, basename="admin-pricelist-items")

urlpatterns = [
    path("pricelists/import/", PriceListImportStubView.as_view(), name="pricelist-import-stub"),
    path("pricelists/export/", PriceListExportStubView.as_view(), name="pricelist-export-stub"),
    path("", include(router.urls)),
]
