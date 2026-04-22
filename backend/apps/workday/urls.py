from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompletedWorkViewSet, ReportViewSet, WorkDayViewSet

router = DefaultRouter()
router.register("", WorkDayViewSet, basename="workday")

works_router = DefaultRouter()
works_router.register("works", CompletedWorkViewSet, basename="works")

reports_router = DefaultRouter()
reports_router.register("reports", ReportViewSet, basename="reports")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(works_router.urls)),
    path("", include(reports_router.urls)),
]
