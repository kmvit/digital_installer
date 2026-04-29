import logging
from datetime import date

from django.db import models as dj_models
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import IsAdminScope

from .management.commands.import_objects import import_objects_from_file
from .models import ObjectDocument, ObjectStage, ProjectObject, Stage
from .serializers import (
    ChangeStageSerializer,
    ObjectDocumentSerializer,
    ObjectStageSerializer,
    ProjectObjectDetailSerializer,
    ProjectObjectListSerializer,
    ProjectObjectWriteSerializer,
    StageSerializer,
)

logger = logging.getLogger(__name__)


class StageViewSet(viewsets.ModelViewSet):
    """CRUD справочника стадий."""

    serializer_class = StageSerializer
    permission_classes = [IsAdminScope]
    queryset = Stage.objects.all()


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
            .select_related("current_stage", "project_manager", "brigade")
            .prefetch_related("object_stages__stage", "documents")
        )

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

        decision_status = self.request.query_params.get("decision_status")
        if decision_status:
            qs = qs.filter(decision_status=decision_status)
        construction_status = self.request.query_params.get("construction_status")
        if construction_status:
            qs = qs.filter(construction_status=construction_status)
        materials_status = self.request.query_params.get("materials_status")
        if materials_status:
            qs = qs.filter(materials_status=materials_status)
        pir_status = self.request.query_params.get("pir_status")
        if pir_status:
            qs = qs.filter(pir_status=pir_status)
        as_built_status = self.request.query_params.get("as_built_status")
        if as_built_status:
            qs = qs.filter(as_built_status=as_built_status)

        return qs

    # --- PATCH /api/admin/objects/{id}/stage/ ---
    @action(detail=True, methods=["patch"], url_path="stage")
    def change_stage(self, request, pk=None):
        obj = self.get_object()
        ser = ChangeStageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        stage_id = ser.validated_data["stage_id"]
        actual = ser.validated_data.get("actual_date") or date.today()

        try:
            new_stage = Stage.objects.get(pk=stage_id)
        except Stage.DoesNotExist:
            return Response(
                {"detail": "Стадия не найдена в справочнике."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # фиксируем фактическую дату на текущей стадии
        if obj.current_stage:
            ObjectStage.objects.filter(
                project_object=obj, stage=obj.current_stage,
            ).update(actual_date=actual)

        # создаём привязку новой стадии если её ещё нет
        ObjectStage.objects.get_or_create(
            project_object=obj, stage=new_stage,
        )

        obj.current_stage = new_stage
        obj.save(update_fields=["current_stage", "updated_at"])

        return Response(ProjectObjectDetailSerializer(obj).data)

    # --- GET/POST /api/admin/objects/{id}/stages/ ---
    @action(detail=True, methods=["get", "post"], url_path="stages")
    def manage_stages(self, request, pk=None):
        obj = self.get_object()

        if request.method == "GET":
            qs = obj.object_stages.select_related("stage")
            return Response(ObjectStageSerializer(qs, many=True).data)

        ser = ObjectStageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(project_object=obj)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    # --- GET/POST /api/admin/objects/{id}/documents/ ---
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


    # --- POST /api/admin/objects/import/ ---
    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def import_xlsx(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "Файл не передан. Ожидается поле 'file' с xlsx."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not file.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "Поддерживаются только файлы .xlsx"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sheet = request.data.get("sheet") or None
        try:
            result = import_objects_from_file(file, sheet=sheet)
        except Exception as exc:
            logger.exception("Ошибка импорта объектов")
            return Response(
                {"detail": f"Ошибка импорта: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "created": result["created"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "errors": result["errors"],
        })


class ObjectStageViewSet(viewsets.ModelViewSet):
    """CRUD привязок стадий к объектам."""

    serializer_class = ObjectStageSerializer
    permission_classes = [IsAdminScope]
    queryset = ObjectStage.objects.select_related("stage", "project_object")


class ObjectDocumentViewSet(viewsets.ModelViewSet):
    """CRUD документов объектов."""

    serializer_class = ObjectDocumentSerializer
    permission_classes = [IsAdminScope]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    queryset = ObjectDocument.objects.select_related("uploaded_by")
