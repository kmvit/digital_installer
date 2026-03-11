from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrigadeViewSet, UserAdminViewSet

router = DefaultRouter()
router.register(r"users", UserAdminViewSet, basename="admin-users")
router.register(r"brigades", BrigadeViewSet, basename="admin-brigades")

urlpatterns = [
    path("", include(router.urls)),
]
