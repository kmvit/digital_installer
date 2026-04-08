from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompletedWorkViewSet, WorkDayViewSet

router = DefaultRouter()
router.register("", WorkDayViewSet, basename="workday")

works_router = DefaultRouter()
works_router.register("works", CompletedWorkViewSet, basename="works")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(works_router.urls)),
]
