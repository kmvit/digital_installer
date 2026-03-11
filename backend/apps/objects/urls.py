from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProjectObjectViewSet

router = DefaultRouter()
router.register(r"objects", ProjectObjectViewSet, basename="admin-objects")

urlpatterns = [
    path("", include(router.urls)),
]
