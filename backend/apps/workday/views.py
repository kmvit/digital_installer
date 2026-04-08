from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.objects.models import ProjectObject
from apps.objects.serializers import ProjectObjectListSerializer
from apps.users.models import Brigade

from .models import (
    CompletedWork,
    EquipmentCheckItem,
    EquipmentChecklist,
    ObjectSession,
    WorkDay,
    WorkDayStatus,
    WorkPhoto,
)
from .permissions import IsApprover, IsAuthenticated, IsForemanOrWorker
from .serializers import (
    ApproveRejectSerializer,
    ArriveSerializer,
    ClockInSerializer,
    ClockOutSerializer,
    CompletedWorkSerializer,
    CompletedWorkWriteSerializer,
    DepartSerializer,
    EquipmentChecklistSerializer,
    EquipmentChecklistWriteSerializer,
    ObjectSessionListSerializer,
    ObjectSessionSerializer,
    WorkDayDetailSerializer,
    WorkDayListSerializer,
    WorkPhotoSerializer,
)
from .utils import check_proximity


# ---------------------------------------------------------------------------
# Рабочий день — основной ViewSet
# ---------------------------------------------------------------------------

class WorkDayViewSet(GenericViewSet):
    """
    Рабочий день бригады.
    Эндпоинты: clock-in, clock-out, current, history, detail,
    arrive, depart, sessions, equipment, approve, reject, summary.
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        return (
            WorkDay.objects
            .select_related("brigade", "foreman", "approved_by")
            .prefetch_related("workers_present", "sessions", "equipment_checklists")
        )

    def get_serializer_class(self):
        return WorkDayDetailSerializer

    # --- Моя бригада (для мобильного) ---
    @action(detail=False, methods=["get"], url_path="my-brigade", permission_classes=[IsForemanOrWorker])
    def my_brigade(self, request):
        user = request.user
        brigade = user.foreman_brigades.first()
        if not brigade:
            brigade = user.brigades.first()
        if not brigade:
            return Response({"error": "Вы не состоите ни в одной бригаде."}, status=status.HTTP_404_NOT_FOUND)

        members = brigade.members.all()
        return Response({
            "id": brigade.id,
            "name": brigade.name,
            "foreman": brigade.foreman_id,
            "members": [
                {"id": m.id, "username": m.username, "first_name": m.first_name, "last_name": m.last_name}
                for m in members
            ],
        })

    # --- Мои объекты (для мобильного) ---
    @action(detail=False, methods=["get"], url_path="my-objects", permission_classes=[IsForemanOrWorker])
    def my_objects(self, request):
        user = request.user
        brigade = user.foreman_brigades.first()
        if not brigade:
            brigade = user.brigades.first()

        objects = ProjectObject.objects.filter(is_archived=False)
        if brigade:
            objects = objects.filter(brigade=brigade)

        return Response(ProjectObjectListSerializer(objects, many=True).data)

    # --- Позиции прайса для объекта (для мобильного) ---
    @action(detail=False, methods=["get"], url_path="price-items", permission_classes=[IsForemanOrWorker])
    def price_items(self, request):
        from apps.pricing.models import PriceListItem
        from apps.pricing.serializers import PriceListItemSerializer
        price_list_id = request.query_params.get("price_list")
        qs = PriceListItem.objects.all()
        if price_list_id:
            qs = qs.filter(price_list_id=price_list_id)
        return Response(PriceListItemSerializer(qs[:500], many=True).data)

    # --- Clock-in ---
    @action(detail=False, methods=["post"], url_path="clock-in", permission_classes=[IsForemanOrWorker])
    def clock_in(self, request):
        serializer = ClockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        brigade = user.foreman_brigades.first()
        if not brigade:
            return Response(
                {"error": "Вы не назначены бригадиром ни одной бригады."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверка: нет ли открытого дня
        open_day = WorkDay.objects.filter(brigade=brigade, status=WorkDayStatus.OPEN).first()
        if open_day:
            return Response(
                {"error": f"У бригады уже есть открытый рабочий день {open_day.date}. Сначала завершите смену."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        workday = WorkDay.objects.create(
            brigade=brigade,
            foreman=user,
            date=now.date(),
            clock_in_at=now,
            clock_in_photo=data["photo"],
            clock_in_latitude=data.get("latitude"),
            clock_in_longitude=data.get("longitude"),
            status=WorkDayStatus.OPEN,
        )

        # Отметить присутствующих
        worker_ids = data.get("workers_present", [])
        if worker_ids:
            workday.workers_present.set(worker_ids)

        return Response(
            WorkDayDetailSerializer(workday).data,
            status=status.HTTP_201_CREATED,
        )

    # --- Clock-out ---
    @action(detail=False, methods=["post"], url_path="clock-out", permission_classes=[IsForemanOrWorker])
    def clock_out(self, request):
        serializer = ClockOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        brigade = user.foreman_brigades.first()
        if not brigade:
            return Response(
                {"error": "Вы не назначены бригадиром ни одной бригады."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workday = WorkDay.objects.filter(brigade=brigade, status=WorkDayStatus.OPEN).first()
        if not workday:
            return Response(
                {"error": "Нет открытого рабочего дня для завершения."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        # Автоматически закрыть незакрытые сессии
        open_sessions = workday.sessions.filter(departed_at__isnull=True)
        open_sessions.update(departed_at=now)

        workday.clock_out_at = now
        workday.clock_out_photo = data["photo"]
        workday.clock_out_latitude = data.get("latitude")
        workday.clock_out_longitude = data.get("longitude")
        workday.status = WorkDayStatus.CLOSED
        workday.save()

        return Response(WorkDayDetailSerializer(workday).data)

    # --- Текущий открытый день ---
    @action(detail=False, methods=["get"], url_path="current", permission_classes=[IsForemanOrWorker])
    def current(self, request):
        user = request.user
        brigade = user.foreman_brigades.first() or user.brigades.first()
        if not brigade:
            return Response(
                {"error": "Вы не состоите ни в одной бригаде."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workday = (
            self.get_queryset()
            .filter(brigade=brigade, status=WorkDayStatus.OPEN)
            .first()
        )
        if not workday:
            return Response({"detail": "Нет открытого рабочего дня."}, status=status.HTTP_404_NOT_FOUND)

        return Response(WorkDayDetailSerializer(workday).data)

    # --- История ---
    @action(detail=False, methods=["get"], url_path="history", permission_classes=[IsAuthenticated])
    def history(self, request):
        qs = self.get_queryset()

        # Фильтры
        brigade_id = request.query_params.get("brigade")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        wd_status = request.query_params.get("status")

        if brigade_id:
            qs = qs.filter(brigade_id=brigade_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if wd_status:
            qs = qs.filter(status=wd_status)

        return Response(WorkDayListSerializer(qs[:100], many=True).data)

    # --- Детали рабочего дня ---
    @action(detail=True, methods=["get"], url_path="detail", permission_classes=[IsAuthenticated])
    def detail_view(self, request, pk=None):
        workday = self.get_queryset().filter(pk=pk).first()
        if not workday:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(WorkDayDetailSerializer(workday).data)

    # --- Прибытие на объект ---
    @action(detail=True, methods=["post"], url_path="arrive", permission_classes=[IsForemanOrWorker])
    def arrive(self, request, pk=None):
        workday = WorkDay.objects.filter(pk=pk, status=WorkDayStatus.OPEN).first()
        if not workday:
            return Response(
                {"error": "Рабочий день не найден или уже закрыт."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ArriveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project_object = ProjectObject.objects.filter(pk=data["project_object"]).first()
        if not project_object:
            return Response(
                {"error": "Объект не найден."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        # GPS-проверка
        proximity = None
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat and lng:
            proximity = check_proximity(float(lat), float(lng), project_object)

        session = ObjectSession.objects.create(
            workday=workday,
            project_object=project_object,
            arrived_at=now,
            arrived_photo=data["photo"],
            arrived_latitude=lat,
            arrived_longitude=lng,
        )

        response_data = ObjectSessionSerializer(session).data
        if proximity:
            response_data["proximity"] = proximity

        return Response(response_data, status=status.HTTP_201_CREATED)

    # --- Убытие с объекта ---
    @action(detail=True, methods=["post"], url_path="depart", permission_classes=[IsForemanOrWorker])
    def depart(self, request, pk=None):
        serializer = DepartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = ObjectSession.objects.filter(
            pk=data["session_id"],
            workday_id=pk,
            departed_at__isnull=True,
        ).first()
        if not session:
            return Response(
                {"error": "Сессия не найдена или уже закрыта."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        session.departed_at = now
        session.departed_photo = data["photo"]
        session.departed_latitude = data.get("latitude")
        session.departed_longitude = data.get("longitude")
        session.save()

        return Response(ObjectSessionSerializer(session).data)

    # --- Список сессий за день ---
    @action(detail=True, methods=["get"], url_path="sessions", permission_classes=[IsAuthenticated])
    def sessions(self, request, pk=None):
        sessions = ObjectSession.objects.filter(workday_id=pk).select_related("project_object")
        return Response(ObjectSessionListSerializer(sessions, many=True).data)

    # --- Чек-лист оборудования ---
    @action(detail=True, methods=["get", "post"], url_path="equipment", permission_classes=[IsForemanOrWorker])
    def equipment(self, request, pk=None):
        workday = WorkDay.objects.filter(pk=pk).first()
        if not workday:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            checklists = (
                EquipmentChecklist.objects
                .filter(workday=workday)
                .prefetch_related("items")
                .select_related("created_by")
            )
            return Response(EquipmentChecklistSerializer(checklists, many=True).data)

        # POST — создать чек-лист
        serializer = EquipmentChecklistWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        checklist = EquipmentChecklist.objects.create(
            workday=workday,
            checklist_type=data["checklist_type"],
            created_by=request.user,
            notes=data.get("notes", ""),
        )

        for item_data in data["items"]:
            EquipmentCheckItem.objects.create(checklist=checklist, **item_data)

        return Response(
            EquipmentChecklistSerializer(checklist).data,
            status=status.HTTP_201_CREATED,
        )

    # --- Сравнение утро/вечер ---
    @action(detail=True, methods=["get"], url_path="equipment/diff", permission_classes=[IsAuthenticated])
    def equipment_diff(self, request, pk=None):
        morning = (
            EquipmentChecklist.objects
            .filter(workday_id=pk, checklist_type="morning")
            .prefetch_related("items")
            .first()
        )
        evening = (
            EquipmentChecklist.objects
            .filter(workday_id=pk, checklist_type="evening")
            .prefetch_related("items")
            .first()
        )

        diff = []
        if morning and evening:
            morning_items = {item.name: item.status for item in morning.items.all()}
            evening_items = {item.name: item.status for item in evening.items.all()}

            all_names = set(morning_items.keys()) | set(evening_items.keys())
            for name in sorted(all_names):
                m_status = morning_items.get(name)
                e_status = evening_items.get(name)
                if m_status != e_status:
                    diff.append({
                        "name": name,
                        "morning": m_status,
                        "evening": e_status,
                        "issue": e_status is None or e_status != "ok",
                    })

        return Response({
            "morning": EquipmentChecklistSerializer(morning).data if morning else None,
            "evening": EquipmentChecklistSerializer(evening).data if evening else None,
            "diff": diff,
        })

    # --- Приёмка отчёта ---
    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsApprover])
    def approve(self, request, pk=None):
        workday = WorkDay.objects.filter(pk=pk).first()
        if not workday:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if workday.status != WorkDayStatus.CLOSED:
            return Response(
                {"error": f"Отчёт в статусе '{workday.get_status_display()}'. Принять можно только закрытый."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workday.status = WorkDayStatus.APPROVED
        workday.approved_by = request.user
        workday.approved_at = timezone.now()
        workday.pm_comment = serializer.validated_data.get("comment", "")
        workday.save()

        return Response(WorkDayDetailSerializer(workday).data)

    # --- Отклонение отчёта ---
    @action(detail=True, methods=["post"], url_path="reject", permission_classes=[IsApprover])
    def reject(self, request, pk=None):
        workday = WorkDay.objects.filter(pk=pk).first()
        if not workday:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if workday.status != WorkDayStatus.CLOSED:
            return Response(
                {"error": f"Отчёт в статусе '{workday.get_status_display()}'. Отклонить можно только закрытый."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workday.status = WorkDayStatus.REJECTED
        workday.pm_comment = serializer.validated_data.get("comment", "")
        workday.save()

        return Response(WorkDayDetailSerializer(workday).data)

    # --- Ожидающие приёмки ---
    @action(detail=False, methods=["get"], url_path="pending-approval", permission_classes=[IsApprover])
    def pending_approval(self, request):
        qs = self.get_queryset().filter(status=WorkDayStatus.CLOSED)
        return Response(WorkDayListSerializer(qs, many=True).data)

    # --- Саммари дня ---
    @action(detail=True, methods=["get"], url_path="summary", permission_classes=[IsAuthenticated])
    def summary(self, request, pk=None):
        workday = (
            self.get_queryset()
            .filter(pk=pk)
            .prefetch_related(
                "sessions__completed_works__price_list_item",
                "sessions__completed_works__photos",
                "sessions__project_object",
                "equipment_checklists__items",
            )
            .first()
        )
        if not workday:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Общее время
        total_hours = None
        if workday.clock_in_at and workday.clock_out_at:
            total_hours = round(
                (workday.clock_out_at - workday.clock_in_at).total_seconds() / 3600, 2
            )

        # Сессии и работы
        sessions_data = []
        total_works = 0
        total_cost = Decimal("0")
        works_without_photos = 0

        for session in workday.sessions.all():
            session_works = []
            session_duration = None
            if session.arrived_at and session.departed_at:
                session_duration = round(
                    (session.departed_at - session.arrived_at).total_seconds() / 60
                )

            for work in session.completed_works.all():
                cost = Decimal("0")
                if work.price_list_item.base_rate:
                    cost = work.volume * work.price_list_item.base_rate
                total_cost += cost
                total_works += 1
                has_photos = work.photos.exists()
                if not has_photos:
                    works_without_photos += 1
                session_works.append({
                    "id": work.id,
                    "name": work.price_list_item.name,
                    "volume": str(work.volume),
                    "unit": work.price_list_item.unit,
                    "rate": str(work.price_list_item.base_rate or 0),
                    "cost": str(cost),
                    "has_photos": has_photos,
                })

            sessions_data.append({
                "object": session.project_object.name,
                "arrived_at": session.arrived_at.isoformat(),
                "departed_at": session.departed_at.isoformat() if session.departed_at else None,
                "duration_minutes": session_duration,
                "works": session_works,
            })

        # Оборудование
        morning_cl = workday.equipment_checklists.filter(checklist_type="morning").first()
        evening_cl = workday.equipment_checklists.filter(checklist_type="evening").first()

        equipment_diff = []
        if morning_cl and evening_cl:
            m_items = {i.name: i.status for i in morning_cl.items.all()}
            e_items = {i.name: i.status for i in evening_cl.items.all()}
            for name in set(m_items) | set(e_items):
                if m_items.get(name) != e_items.get(name):
                    equipment_diff.append({
                        "name": name,
                        "morning": m_items.get(name),
                        "evening": e_items.get(name),
                    })

        return Response({
            "workday_id": workday.id,
            "date": workday.date,
            "brigade": workday.brigade.name,
            "foreman": workday.foreman.get_full_name() or workday.foreman.username,
            "status": workday.status,
            "total_hours": total_hours,
            "sessions": sessions_data,
            "total_works": total_works,
            "total_cost": str(total_cost),
            "works_without_photos": works_without_photos,
            "equipment_morning": EquipmentChecklistSerializer(morning_cl).data if morning_cl else None,
            "equipment_evening": EquipmentChecklistSerializer(evening_cl).data if evening_cl else None,
            "equipment_diff": equipment_diff,
        })


# ---------------------------------------------------------------------------
# Выполненные работы — CRUD
# ---------------------------------------------------------------------------

class CompletedWorkViewSet(GenericViewSet):
    """CRUD для выполненных работ."""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [IsForemanOrWorker]

    def get_queryset(self):
        return CompletedWork.objects.select_related(
            "price_list_item", "created_by", "object_session",
        ).prefetch_related("photos")

    # Список работ в сессии
    @action(detail=False, methods=["get", "post"], url_path="by-session/(?P<session_id>[0-9]+)")
    def by_session(self, request, session_id=None):
        session = ObjectSession.objects.filter(pk=session_id).first()
        if not session:
            return Response({"error": "Сессия не найдена."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            works = self.get_queryset().filter(object_session=session)
            return Response(CompletedWorkSerializer(works, many=True).data)

        # POST
        serializer = CompletedWorkWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        work = serializer.save(
            object_session=session,
            created_by=request.user,
        )
        return Response(
            CompletedWorkSerializer(work).data,
            status=status.HTTP_201_CREATED,
        )

    # Редактировать / удалить работу
    @action(detail=True, methods=["patch", "delete"], url_path="manage")
    def manage(self, request, pk=None):
        work = self.get_queryset().filter(pk=pk).first()
        if not work:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            work.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        serializer = CompletedWorkWriteSerializer(work, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CompletedWorkSerializer(work).data)

    # Добавить фото к работе
    @action(detail=True, methods=["post"], url_path="photos")
    def add_photo(self, request, pk=None):
        work = CompletedWork.objects.filter(pk=pk).first()
        if not work:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = WorkPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(completed_work=work)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
