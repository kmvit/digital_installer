from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HealthcheckView, SystemSettingViewSet

router = DefaultRouter()
router.register(r"admin/settings", SystemSettingViewSet, basename="admin-settings")

urlpatterns = [
    path("health/", HealthcheckView.as_view(), name="healthcheck"),
    path("", include(router.urls)),
]
