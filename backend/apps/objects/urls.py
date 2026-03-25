from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ObjectDocumentViewSet, ObjectStageViewSet, ProjectObjectViewSet, StageViewSet

router = DefaultRouter()
router.register(r"stages", StageViewSet, basename="admin-stages")
router.register(r"objects", ProjectObjectViewSet, basename="admin-objects")
router.register(r"object-stages", ObjectStageViewSet, basename="admin-object-stages")
router.register(r"object-documents", ObjectDocumentViewSet, basename="admin-object-documents")

urlpatterns = [
    path("", include(router.urls)),
]
