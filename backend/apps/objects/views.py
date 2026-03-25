from datetime import date

from django.db import models as dj_models
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import IsAdminScope

from .models import ObjectDocument, ObjectStage, ProjectObject
from .serializers import (
    ChangeStageSerializer,
    ObjectDocumentSerializer,
    ObjectStageSerializer,
    ProjectObjectDetailSerializer,
    ProjectObjectListSerializer,
    ProjectObjectWriteSerializer,
)


class ProjectObjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminScope]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectObjectListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectObjectWriteSerializer
        return ProjectObjectDetailSerializer

    def get_queryset(self):
        qs = (
            ProjectObject.objects
            .select_related("price_list", "current_stage", "project_manager", "brigade")
            .prefetch_related("stages", "documents")
        )

        # фильтры
        price_list = self.request.query_params.get("price_list")
        if price_list:
            qs = qs.filter(price_list_id=price_list)

        archived = self.request.query_params.get("archived")
        if archived is not None:
            qs = qs.filter(is_archived=archived.lower() in ("1", "true", "yes"))

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                dj_models.Q(name__icontains=search)
                | dj_models.Q(address__icontains=search)
                | dj_models.Q(customer__icontains=search)
            )

        return qs

    def perform_create(self, serializer):
        serializer.save()

    # --- смена стадии: PATCH /api/admin/objects/{id}/stage/ ---
    @action(detail=True, methods=["patch"], url_path="stage")
    def change_stage(self, request, pk=None):
        obj = self.get_object()
        ser = ChangeStageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        stage_id = ser.validated_data["stage_id"]
        actual = ser.validated_data.get("actual_date") or date.today()

        try:
            new_stage = obj.stages.get(pk=stage_id)
        except ObjectStage.DoesNotExist:
            return Response(
                {"detail": "Стадия не принадлежит данному объекту."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # фиксируем фактическую дату на предыдущей стадии
        if obj.current_stage and obj.current_stage != new_stage:
            obj.current_stage.actual_date = actual
            obj.current_stage.save(update_fields=["actual_date"])

        obj.current_stage = new_stage
        obj.save(update_fields=["current_stage", "updated_at"])

        return Response(ProjectObjectDetailSerializer(obj).data)

    # --- управление стадиями: GET / POST /api/admin/objects/{id}/stages/ ---
    @action(detail=True, methods=["get", "post"], url_path="stages")
    def manage_stages(self, request, pk=None):
        obj = self.get_object()

        if request.method == "GET":
            stages = obj.stages.all()
            return Response(ObjectStageSerializer(stages, many=True).data)

        ser = ObjectStageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(project_object=obj)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    # --- загрузка документов: GET / POST /api/admin/objects/{id}/documents/ ---
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="documents",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def manage_documents(self, request, pk=None):
        obj = self.get_object()

        if request.method == "GET":
            docs = obj.documents.select_related("uploaded_by")
            return Response(ObjectDocumentSerializer(docs, many=True).data)

        ser = ObjectDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(project_object=obj, uploaded_by=request.user)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class ObjectStageViewSet(viewsets.ModelViewSet):
    """CRUD отдельных стадий (PUT/PATCH/DELETE)."""

    serializer_class = ObjectStageSerializer
    permission_classes = [IsAdminScope]
    queryset = ObjectStage.objects.select_related("project_object")


class ObjectDocumentViewSet(viewsets.ModelViewSet):
    """CRUD отдельных документов (PUT/PATCH/DELETE)."""

    serializer_class = ObjectDocumentSerializer
    permission_classes = [IsAdminScope]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    queryset = ObjectDocument.objects.select_related("uploaded_by")
