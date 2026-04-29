import csv
import io
from decimal import Decimal

from django.conf import settings as django_settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.objects.models import ProjectObject
from apps.objects.serializers import ProjectObjectListSerializer
from apps.users.models import Brigade
from apps.users.models import RoleCode

from .models import (
    BrigadeGpsCheck,
    CompletedWork,
    EquipmentCheckItem,
    EquipmentChecklist,
    ObjectSession,
    WorkDay,
    WorkDayStatus,
    WorkPhoto,
    WorkStatus,
)
from .permissions import IsApprover, IsAuthenticated, IsForeman, IsForemanOrWorker
from .serializers import (
    ApproveRejectSerializer,
    ArriveSerializer,
    BrigadeGpsCheckSerializer,
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
    WorkStartFinishSerializer,
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
        from apps.objects.models import ProjectObject
        from apps.pricing.models import PriceListItem
        from apps.pricing.serializers import PriceListItemSerializer

        price_list_id = request.query_params.get("price_list")
        object_id = request.query_params.get("object_id")
        session_id = request.query_params.get("session_id")

        project_object = None
        if object_id:
            project_object = ProjectObject.objects.filter(pk=object_id).first()
        elif session_id:
            session = ObjectSession.objects.filter(pk=session_id).select_related("project_object").first()
            if session:
                project_object = session.project_object

        if project_object:
            allowed_types = project_object.available_work_types.all()
            if allowed_types.exists():
                qs = PriceListItem.objects.filter(work_type__in=allowed_types)
            else:
                qs = PriceListItem.objects.none()
        else:
            qs = PriceListItem.objects.all()
            if price_list_id:
                qs = qs.filter(price_list_id=price_list_id)

        return Response(PriceListItemSerializer(qs[:500], many=True).data)

    # --- Clock-in ---
    @action(detail=False, methods=["post"], url_path="clock-in", permission_classes=[IsForeman])
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
    @action(detail=False, methods=["post"], url_path="clock-out", permission_classes=[IsForeman])
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
    @action(detail=True, methods=["post"], url_path="arrive", permission_classes=[IsForeman])
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

        # GPS-проверка — блокируем «Прибытие», если вне зоны объекта.
        # В тестовом режиме (WORKDAY_BYPASS_GPS=1) проверка отключается.
        bypass_gps = getattr(django_settings, "WORKDAY_BYPASS_GPS", False)
        proximity = None
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat and lng:
            proximity = check_proximity(float(lat), float(lng), project_object)
            obj_has_coords = project_object.latitude and project_object.longitude
            if obj_has_coords and not proximity["within_zone"] and not bypass_gps:
                return Response(
                    {
                        "error": proximity.get("warning") or "Вы находитесь вне зоны объекта.",
                        "proximity": proximity,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif not bypass_gps:
            return Response(
                {"error": "Не удалось определить GPS — отметка прибытия невозможна."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
    @action(detail=True, methods=["post"], url_path="depart", permission_classes=[IsForeman])
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
        session.scheme_photo = data["scheme_photo"]
        session.departed_latitude = data.get("latitude")
        session.departed_longitude = data.get("longitude")
        session.save()

        return Response(ObjectSessionSerializer(session).data)

    # --- GPS-чек члена бригады при завершении смены ---
    @action(detail=True, methods=["get", "post"], url_path="gps-check", permission_classes=[IsForemanOrWorker])
    def gps_check(self, request, pk=None):
        workday = WorkDay.objects.filter(pk=pk, status=WorkDayStatus.OPEN).first()
        if not workday:
            return Response({"error": "Смена не найдена или закрыта."}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "GET":
            checks = workday.gps_checks.select_related("user")
            members = [
                {
                    "id": u.id,
                    "name": u.get_full_name() or u.username,
                    "checked": False, "latitude": None, "longitude": None, "captured_at": None,
                }
                for u in workday.workers_present.all()
            ]
            checks_by_user = {c.user_id: c for c in checks}
            for m in members:
                c = checks_by_user.get(m["id"])
                if c:
                    m.update(
                        checked=True,
                        latitude=str(c.latitude),
                        longitude=str(c.longitude),
                        captured_at=c.captured_at.isoformat(),
                    )
            return Response(members)

        # POST — пользователь сам подтверждает свою GPS-метку
        serializer = BrigadeGpsCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        check, _ = BrigadeGpsCheck.objects.update_or_create(
            workday=workday, user=request.user,
            defaults={
                "latitude": data["latitude"],
                "longitude": data["longitude"],
                "captured_at": data["captured_at"],
            },
        )
        return Response(BrigadeGpsCheckSerializer(check).data, status=status.HTTP_200_OK)

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
        from datetime import timedelta
        qs = self.get_queryset().filter(status=WorkDayStatus.CLOSED).order_by("date")
        rows = []
        today = timezone.localdate()
        for wd in qs:
            overdue_days = (today - wd.date).days if wd.date else 0
            data = WorkDayListSerializer(wd).data
            data["overdue_days"] = overdue_days
            data["is_overdue"] = overdue_days >= 1
            rows.append(data)
        return Response(rows)

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

        def _photo_url(field):
            try:
                return request.build_absolute_uri(field.url) if field else None
            except Exception:
                return None

        # Сессии и работы
        sessions_data = []
        total_works = 0
        total_cost = Decimal("0")
        works_without_photos = 0
        sessions_without_scheme = 0

        for session in workday.sessions.all():
            session_works = []
            session_duration = None
            if session.arrived_at and session.departed_at:
                session_duration = round(
                    (session.departed_at - session.arrived_at).total_seconds() / 60
                )
            if session.departed_at and not session.scheme_photo:
                sessions_without_scheme += 1

            for work in session.completed_works.all():
                cost = Decimal("0")
                if work.price_list_item.base_rate:
                    cost = work.volume * work.price_list_item.base_rate
                if work.status == WorkStatus.COMPLETED:
                    total_cost += cost
                total_works += 1
                has_photos = bool(work.photos.exists() or work.started_photo or work.completed_photo)
                if not has_photos:
                    works_without_photos += 1
                session_works.append({
                    "id": work.id,
                    "name": work.price_list_item.name,
                    "volume": str(work.volume),
                    "planned_volume": str(work.planned_volume) if work.planned_volume else None,
                    "unit": work.price_list_item.unit,
                    "rate": str(work.price_list_item.base_rate or 0),
                    "cost": str(cost),
                    "status": work.status,
                    "assigned_to_name": (
                        work.assigned_to.get_full_name() or work.assigned_to.username
                    ) if work.assigned_to else None,
                    "has_photos": has_photos,
                    "started_photo": _photo_url(work.started_photo),
                    "completed_photo": _photo_url(work.completed_photo),
                    "comment": work.comment or "",
                    "extra_photos": [
                        _photo_url(p.photo) for p in work.photos.all()
                    ],
                })

            sessions_data.append({
                "session_id": session.id,
                "object": session.project_object.name,
                "arrived_at": session.arrived_at.isoformat(),
                "departed_at": session.departed_at.isoformat() if session.departed_at else None,
                "duration_minutes": session_duration,
                "arrived_photo": _photo_url(session.arrived_photo),
                "departed_photo": _photo_url(session.departed_photo),
                "scheme_photo": _photo_url(session.scheme_photo),
                "arrived_lat": str(session.arrived_latitude) if session.arrived_latitude else None,
                "arrived_lng": str(session.arrived_longitude) if session.arrived_longitude else None,
                "departed_lat": str(session.departed_latitude) if session.departed_latitude else None,
                "departed_lng": str(session.departed_longitude) if session.departed_longitude else None,
                "works": session_works,
            })

        # GPS-чек членов бригады
        gps_checks = []
        check_by_user = {c.user_id: c for c in workday.gps_checks.select_related("user")}
        for u in workday.workers_present.all():
            c = check_by_user.get(u.id)
            gps_checks.append({
                "user_id": u.id,
                "name": u.get_full_name() or u.username,
                "checked": c is not None,
                "captured_at": c.captured_at.isoformat() if c else None,
                "latitude": str(c.latitude) if c else None,
                "longitude": str(c.longitude) if c else None,
            })
        gps_checks_missing = sum(1 for g in gps_checks if not g["checked"])

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

        # Индикаторы качества для приёмки
        quality = {
            "all_works_have_photos": works_without_photos == 0 and total_works > 0,
            "all_sessions_have_scheme": sessions_without_scheme == 0 and len(sessions_data) > 0,
            "all_workers_gps_checked": gps_checks_missing == 0 and len(gps_checks) > 0,
            "works_without_photos": works_without_photos,
            "sessions_without_scheme": sessions_without_scheme,
            "gps_checks_missing": gps_checks_missing,
        }

        return Response({
            "workday_id": workday.id,
            "date": workday.date,
            "brigade": workday.brigade.name,
            "foreman": workday.foreman.get_full_name() or workday.foreman.username,
            "status": workday.status,
            "pm_comment": workday.pm_comment or "",
            "total_hours": total_hours,
            "clock_in_at": workday.clock_in_at.isoformat() if workday.clock_in_at else None,
            "clock_out_at": workday.clock_out_at.isoformat() if workday.clock_out_at else None,
            "clock_in_photo": _photo_url(workday.clock_in_photo),
            "clock_out_photo": _photo_url(workday.clock_out_photo),
            "clock_in_lat": str(workday.clock_in_latitude) if workday.clock_in_latitude else None,
            "clock_in_lng": str(workday.clock_in_longitude) if workday.clock_in_longitude else None,
            "clock_out_lat": str(workday.clock_out_latitude) if workday.clock_out_latitude else None,
            "clock_out_lng": str(workday.clock_out_longitude) if workday.clock_out_longitude else None,
            "sessions": sessions_data,
            "total_works": total_works,
            "total_cost": str(total_cost),
            "works_without_photos": works_without_photos,
            "gps_checks": gps_checks,
            "quality": quality,
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

        # POST — добавлять работы может только бригадир (мастер) или администратор/директор
        if request.user.role not in (RoleCode.FOREMAN, RoleCode.ADMINISTRATOR, RoleCode.DIRECTOR):
            return Response(
                {"detail": "Добавлять работы может только бригадир."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CompletedWorkWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        price_item = serializer.validated_data.get("price_list_item")
        project_object = session.project_object
        if price_item and project_object:
            allowed_types = project_object.available_work_types.all()
            if allowed_types.exists():
                if price_item.work_type_id is None or not allowed_types.filter(pk=price_item.work_type_id).exists():
                    return Response(
                        {"price_list_item": "Эта работа не входит в виды работ, разрешённые для объекта."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Если назначен исполнитель — это назначение, факт ставится при «Завершил».
        assigned_to = serializer.validated_data.get("assigned_to")
        save_kwargs = {
            "object_session": session,
            "created_by": request.user,
        }
        if assigned_to:
            save_kwargs["status"] = WorkStatus.ASSIGNED
            save_kwargs["assigned_by"] = request.user
        work = serializer.save(**save_kwargs)
        return Response(
            CompletedWorkSerializer(work).data,
            status=status.HTTP_201_CREATED,
        )

    # Редактировать / удалить работу — только бригадир/админ/директор
    @action(detail=True, methods=["patch", "delete"], url_path="manage")
    def manage(self, request, pk=None):
        if request.user.role not in (RoleCode.FOREMAN, RoleCode.ADMINISTRATOR, RoleCode.DIRECTOR):
            return Response(
                {"detail": "Редактировать работы может только бригадир."},
                status=status.HTTP_403_FORBIDDEN,
            )
        work = self.get_queryset().filter(pk=pk).first()
        if not work:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            work.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH — допускаем смену исполнителя/объёмов/статуса
        serializer = CompletedWorkWriteSerializer(work, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        new_status = request.data.get("status")
        if new_status in (WorkStatus.ASSIGNED, WorkStatus.IN_PROGRESS, WorkStatus.COMPLETED):
            work.status = new_status
            work.save(update_fields=["status"])
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

    # Монтажник: «Работу начал»
    @action(detail=True, methods=["post"], url_path="start", permission_classes=[IsForemanOrWorker])
    def start_work(self, request, pk=None):
        work = self.get_queryset().filter(pk=pk).first()
        if not work:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if work.assigned_to_id and work.assigned_to_id != request.user.id:
            return Response({"error": "Эта работа назначена другому монтажнику."}, status=status.HTTP_403_FORBIDDEN)
        if work.status not in (WorkStatus.ASSIGNED,):
            return Response({"error": "Работу нельзя начать в текущем статусе."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WorkStartFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        work.started_at = timezone.now()
        work.started_photo = data["photo"]
        work.started_latitude = data.get("latitude")
        work.started_longitude = data.get("longitude")
        work.status = WorkStatus.IN_PROGRESS
        work.save()
        return Response(CompletedWorkSerializer(work).data)

    # Монтажник: «Работу завершил» (фактический объём + фото)
    @action(detail=True, methods=["post"], url_path="finish", permission_classes=[IsForemanOrWorker])
    def finish_work(self, request, pk=None):
        work = self.get_queryset().filter(pk=pk).first()
        if not work:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if work.assigned_to_id and work.assigned_to_id != request.user.id:
            return Response({"error": "Эта работа назначена другому монтажнику."}, status=status.HTTP_403_FORBIDDEN)
        if work.status not in (WorkStatus.IN_PROGRESS, WorkStatus.ASSIGNED):
            return Response({"error": "Работу нельзя завершить в текущем статусе."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WorkStartFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "volume" in data:
            work.volume = data["volume"]
        work.completed_at = timezone.now()
        work.completed_photo = data["photo"]
        work.completed_latitude = data.get("latitude")
        work.completed_longitude = data.get("longitude")
        work.status = WorkStatus.COMPLETED
        work.save()
        return Response(CompletedWorkSerializer(work).data)

    # Список работ, назначенных текущему монтажнику в открытых сменах
    @action(detail=False, methods=["get"], url_path="my-assignments", permission_classes=[IsForemanOrWorker])
    def my_assignments(self, request):
        qs = self.get_queryset().filter(
            assigned_to=request.user,
            object_session__workday__status=WorkDayStatus.OPEN,
        ).order_by("status", "created_at")
        return Response(CompletedWorkSerializer(qs, many=True).data)


class ReportViewSet(GenericViewSet):
    """Отчётность по рабочим дням: табель, сдельная, акты, экспорт."""

    REPORT_ROLES = {
        RoleCode.ADMINISTRATOR,
        RoleCode.DIRECTOR,
        RoleCode.PROJECT_MANAGER,
        RoleCode.SUPPORT_MANAGER,
        RoleCode.ACCOUNTANT,
    }
    parser_classes = (JSONParser,)

    @staticmethod
    def _pdf_escape(text):
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    def _build_simple_pdf(self, lines):
        """
        Собирает минимальный валидный PDF (A4, Helvetica).
        Используем ASCII-safe текст, чтобы файл гарантированно открывался
        без внешних зависимостей.
        """
        safe_lines = [
            line.encode("latin-1", errors="replace").decode("latin-1")
            for line in lines
        ]

        commands = ["BT", "/F1 10 Tf", "50 800 Td"]
        first = True
        for line in safe_lines:
            if first:
                commands.append(f"({self._pdf_escape(line)}) Tj")
                first = False
            else:
                commands.append(f"0 -14 Td ({self._pdf_escape(line)}) Tj")
        commands.append("ET")
        stream_data = "\n".join(commands).encode("latin-1", errors="replace")

        objects = []
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        objects.append(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>\n"
            b"endobj\n"
        )
        objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        objects.append(
            b"5 0 obj\n"
            + f"<< /Length {len(stream_data)} >>\n".encode("ascii")
            + b"stream\n"
            + stream_data
            + b"\nendstream\nendobj\n"
        )

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)

        xref_pos = len(pdf)
        pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

        pdf.extend(
            (
                "trailer\n"
                f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
                "startxref\n"
                f"{xref_pos}\n"
                "%%EOF\n"
            ).encode("ascii")
        )
        return bytes(pdf)

    def _ensure_report_access(self, request):
        if request.user.role not in self.REPORT_ROLES:
            return Response(
                {"detail": "Недостаточно прав для просмотра отчётности."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def _filtered_workdays(self, request, only_approved=False):
        qs = (
            WorkDay.objects.select_related("brigade", "foreman")
            .prefetch_related("workers_present", "sessions__project_object", "sessions__completed_works__price_list_item")
            .all()
        )
        brigade_id = request.query_params.get("brigade")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        object_id = request.query_params.get("object")
        include_unapproved = request.query_params.get("include_unapproved", "0").lower() in ("1", "true", "yes")

        if brigade_id:
            qs = qs.filter(brigade_id=brigade_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if object_id:
            qs = qs.filter(sessions__project_object_id=object_id).distinct()
        if only_approved and not include_unapproved:
            qs = qs.filter(status=WorkDayStatus.APPROVED)
        return qs.order_by("-date", "-clock_in_at")

    def _timesheet_rows(self, request):
        rows = []
        for wd in self._filtered_workdays(request):
            worker_names = [
                worker.get_full_name() or worker.username
                for worker in wd.workers_present.all()
            ]
            worked_hours = Decimal("0.00")
            overtime_hours = Decimal("0.00")
            if wd.clock_in_at and wd.clock_out_at:
                duration = wd.clock_out_at - wd.clock_in_at
                total_hours = Decimal(duration.total_seconds() / 3600).quantize(Decimal("0.01"))
                worked_hours = total_hours
                overtime_hours = max(total_hours - Decimal("8.00"), Decimal("0.00"))

            rows.append(
                {
                    "workday_id": wd.id,
                    "date": wd.date.isoformat(),
                    "brigade": wd.brigade.name,
                    "foreman": wd.foreman.get_full_name() or wd.foreman.username,
                    "workers": worker_names,
                    "clock_in_at": wd.clock_in_at.isoformat() if wd.clock_in_at else None,
                    "clock_out_at": wd.clock_out_at.isoformat() if wd.clock_out_at else None,
                    "hours": str(worked_hours),
                    "overtime_hours": str(overtime_hours),
                    "status": wd.status,
                }
            )
        return rows

    def _piecework_rows(self, request):
        rows = []
        for wd in self._filtered_workdays(request, only_approved=True):
            for session in wd.sessions.all():
                for work in session.completed_works.all():
                    rate = work.price_list_item.base_rate or Decimal("0")
                    total = (work.volume * rate).quantize(Decimal("0.01"))
                    rows.append(
                        {
                            "workday_id": wd.id,
                            "date": wd.date.isoformat(),
                            "brigade": wd.brigade.name,
                            "object": session.project_object.name,
                            "work_name": work.price_list_item.name,
                            "unit": work.price_list_item.unit,
                            "volume": str(work.volume),
                            "rate": str(rate),
                            "amount": str(total),
                        }
                    )
        return rows

    def _completion_act_rows(self, request):
        grouped = {}
        for row in self._piecework_rows(request):
            key = (row["object"], row["work_name"], row["unit"], row["rate"])
            existing = grouped.get(key)
            current_volume = Decimal(row["volume"])
            current_amount = Decimal(row["amount"])
            if not existing:
                grouped[key] = {
                    "object": row["object"],
                    "work_name": row["work_name"],
                    "unit": row["unit"],
                    "rate": row["rate"],
                    "volume": current_volume,
                    "amount": current_amount,
                }
            else:
                existing["volume"] += current_volume
                existing["amount"] += current_amount
        rows = []
        for item in grouped.values():
            rows.append(
                {
                    "object": item["object"],
                    "work_name": item["work_name"],
                    "unit": item["unit"],
                    "rate": item["rate"],
                    "volume": str(item["volume"].quantize(Decimal("0.001"))),
                    "amount": str(item["amount"].quantize(Decimal("0.01"))),
                }
            )
        return sorted(rows, key=lambda x: (x["object"], x["work_name"]))

    def _kpi_rows(self, request):
        """KPI монтажников: дни/часы/выработка/дисциплина за период.

        Деньги учитываются только для утверждённых смен (если не передан include_unapproved=1).
        """
        from collections import defaultdict
        LATE_HOUR, LATE_MINUTE = 9, 0
        stats: dict[int, dict] = defaultdict(lambda: {
            "user_id": None, "name": "",
            "days": set(), "hours_total": Decimal("0"),
            "amount_total": Decimal("0"),
            "late_count": 0,
            "completed_assignments": 0,
        })

        for wd in self._filtered_workdays(request, only_approved=True):
            if not wd.clock_in_at:
                continue
            members = list(wd.workers_present.all())
            if not members:
                continue

            wd_hours = Decimal("0")
            if wd.clock_out_at:
                wd_hours = Decimal(
                    (wd.clock_out_at - wd.clock_in_at).total_seconds() / 3600
                ).quantize(Decimal("0.01"))

            late = (
                wd.clock_in_at.hour > LATE_HOUR
                or (wd.clock_in_at.hour == LATE_HOUR and wd.clock_in_at.minute > LATE_MINUTE)
            )

            wd_amount = Decimal("0")
            for s in wd.sessions.all():
                for w in s.completed_works.all():
                    if w.status != WorkStatus.COMPLETED:
                        continue
                    rate = w.price_list_item.base_rate or Decimal("0")
                    wd_amount += w.volume * rate
            per_member_amount = (wd_amount / len(members)) if members else Decimal("0")

            for m in members:
                row = stats[m.id]
                row["user_id"] = m.id
                row["name"] = m.get_full_name() or m.username
                row["days"].add(wd.date)
                row["hours_total"] += wd_hours
                row["amount_total"] += per_member_amount
                if late:
                    row["late_count"] += 1

            for s in wd.sessions.all():
                for w in s.completed_works.all():
                    if w.assigned_to_id and w.status == WorkStatus.COMPLETED and w.assigned_to_id in stats:
                        stats[w.assigned_to_id]["completed_assignments"] += 1

        out = []
        for s in stats.values():
            days = len(s["days"])
            hours = s["hours_total"]
            amount = s["amount_total"]
            out.append({
                "user_id": s["user_id"],
                "name": s["name"],
                "days_worked": days,
                "hours_total": str(hours.quantize(Decimal("0.01"))),
                "amount_total": str(amount.quantize(Decimal("0.01"))),
                "amount_per_day": str((amount / days).quantize(Decimal("0.01"))) if days else "0.00",
                "hours_per_day": str((hours / days).quantize(Decimal("0.01"))) if days else "0.00",
                "late_count": s["late_count"],
                "completed_assignments": s["completed_assignments"],
            })
        return sorted(out, key=lambda x: x["name"])

    def _object_time_rows(self, request):
        """Затраты времени по объектам за период."""
        from collections import defaultdict
        stats: dict[int, dict] = defaultdict(lambda: {
            "object_id": None, "object_name": "",
            "session_hours": Decimal("0"),
            "amount_total": Decimal("0"),
            "brigades": set(),
            "session_count": 0,
        })
        for wd in self._filtered_workdays(request):
            for s in wd.sessions.all():
                obj = s.project_object
                row = stats[obj.id]
                row["object_id"] = obj.id
                row["object_name"] = obj.name
                row["brigades"].add(wd.brigade.name)
                row["session_count"] += 1
                if s.arrived_at and s.departed_at:
                    row["session_hours"] += Decimal(
                        (s.departed_at - s.arrived_at).total_seconds() / 3600
                    )
                for w in s.completed_works.all():
                    if w.status != WorkStatus.COMPLETED:
                        continue
                    rate = w.price_list_item.base_rate or Decimal("0")
                    row["amount_total"] += w.volume * rate

        out = []
        for s in stats.values():
            hours = s["session_hours"].quantize(Decimal("0.01"))
            amount = s["amount_total"].quantize(Decimal("0.01"))
            cost_per_hour = (amount / hours).quantize(Decimal("0.01")) if hours else Decimal("0.00")
            out.append({
                "object_id": s["object_id"],
                "object_name": s["object_name"],
                "brigades": sorted(s["brigades"]),
                "session_count": s["session_count"],
                "session_hours": str(hours),
                "amount_total": str(amount),
                "cost_per_hour": str(cost_per_hour),
            })
        return sorted(out, key=lambda x: x["object_name"])

    def _ks2_rows(self, request):
        """КС-2: акт о приёмке выполненных работ за период по объекту.

        Группировка по позиции расценки (наименование/ед./цена) с суммами объёма и стоимости.
        """
        from collections import defaultdict
        grouped: dict[tuple, dict] = {}
        order = 0
        for wd in self._filtered_workdays(request, only_approved=True):
            for s in wd.sessions.all():
                for w in s.completed_works.all():
                    if w.status != WorkStatus.COMPLETED:
                        continue
                    item = w.price_list_item
                    rate = item.base_rate or Decimal("0")
                    key = (s.project_object.name, item.id)
                    g = grouped.get(key)
                    if not g:
                        order += 1
                        g = {
                            "row_number": order,
                            "object": s.project_object.name,
                            "item_number": item.item_number,
                            "work_name": item.name,
                            "unit": item.unit,
                            "volume": Decimal("0"),
                            "rate": rate,
                            "amount": Decimal("0"),
                        }
                        grouped[key] = g
                    g["volume"] += w.volume
                    g["amount"] += w.volume * rate
        rows = []
        for g in grouped.values():
            rows.append({
                "row_number": g["row_number"],
                "object": g["object"],
                "item_number": g["item_number"],
                "work_name": g["work_name"],
                "unit": g["unit"],
                "volume": str(g["volume"].quantize(Decimal("0.001"))),
                "rate": str(g["rate"]),
                "amount": str(g["amount"].quantize(Decimal("0.01"))),
            })
        return sorted(rows, key=lambda r: (r["object"], r["item_number"] or "", r["work_name"]))

    def _ks3_rows(self, request):
        """КС-3: справка о стоимости. Разбивка по объектам.

        Колонки: с начала года · с начала месяца · отчётный период (по фильтру date_from/date_to).
        """
        from collections import defaultdict
        from datetime import date as _date

        today = timezone.localdate()
        year_start = _date(today.year, 1, 1)
        month_start = today.replace(day=1)

        df = request.query_params.get("date_from")
        dt = request.query_params.get("date_to")
        period_start = _date.fromisoformat(df) if df else None
        period_end = _date.fromisoformat(dt) if dt else today

        include_unapproved = request.query_params.get("include_unapproved", "0").lower() in ("1", "true", "yes")
        qs = (
            CompletedWork.objects.filter(status=WorkStatus.COMPLETED)
            .select_related("price_list_item", "object_session__project_object", "object_session__workday")
        )
        if not include_unapproved:
            qs = qs.filter(object_session__workday__status=WorkDayStatus.APPROVED)
        brigade_id = request.query_params.get("brigade")
        object_id = request.query_params.get("object")
        if brigade_id:
            qs = qs.filter(object_session__workday__brigade_id=brigade_id)
        if object_id:
            qs = qs.filter(object_session__project_object_id=object_id)

        per_object = defaultdict(lambda: {"name": "", "year": Decimal("0"), "month": Decimal("0"), "period": Decimal("0"), "total": Decimal("0")})
        for w in qs:
            d = w.object_session.workday.date
            obj_id = w.object_session.project_object_id
            row = per_object[obj_id]
            row["name"] = w.object_session.project_object.name
            rate = w.price_list_item.base_rate or Decimal("0")
            amount = w.volume * rate
            row["total"] += amount
            if d >= year_start:
                row["year"] += amount
            if d >= month_start:
                row["month"] += amount
            if (period_start is None or d >= period_start) and d <= period_end:
                row["period"] += amount

        rows = []
        for r in per_object.values():
            rows.append({
                "object": r["name"],
                "amount_year": str(r["year"].quantize(Decimal("0.01"))),
                "amount_month": str(r["month"].quantize(Decimal("0.01"))),
                "amount_period": str(r["period"].quantize(Decimal("0.01"))),
                "amount_total": str(r["total"].quantize(Decimal("0.01"))),
            })
        return sorted(rows, key=lambda r: r["object"])

    def _ks11_rows(self, request):
        """КС-11: акт приёмки законченного строительством объекта.

        Одна строка на объект — итоговая сумма работ + дата сдачи (= последняя дата работ либо deadline).
        """
        include_unapproved = request.query_params.get("include_unapproved", "0").lower() in ("1", "true", "yes")
        qs = (
            CompletedWork.objects.filter(status=WorkStatus.COMPLETED)
            .select_related("price_list_item", "object_session__project_object", "object_session__workday")
        )
        if not include_unapproved:
            qs = qs.filter(object_session__workday__status=WorkDayStatus.APPROVED)
        object_id = request.query_params.get("object")
        if object_id:
            qs = qs.filter(object_session__project_object_id=object_id)
        df = request.query_params.get("date_from")
        dt = request.query_params.get("date_to")
        if df:
            qs = qs.filter(object_session__workday__date__gte=df)
        if dt:
            qs = qs.filter(object_session__workday__date__lte=dt)

        from collections import defaultdict
        per_obj = defaultdict(lambda: {
            "object_id": None, "name": "", "deadline": None,
            "amount": Decimal("0"), "last_work_date": None, "first_work_date": None,
        })
        for w in qs:
            obj = w.object_session.project_object
            row = per_obj[obj.id]
            row["object_id"] = obj.id
            row["name"] = obj.name
            row["deadline"] = obj.deadline
            rate = w.price_list_item.base_rate or Decimal("0")
            row["amount"] += w.volume * rate
            d = w.object_session.workday.date
            if row["last_work_date"] is None or d > row["last_work_date"]:
                row["last_work_date"] = d
            if row["first_work_date"] is None or d < row["first_work_date"]:
                row["first_work_date"] = d
        rows = []
        for r in per_obj.values():
            rows.append({
                "object_id": r["object_id"],
                "object": r["name"],
                "first_work_date": r["first_work_date"].isoformat() if r["first_work_date"] else None,
                "last_work_date": r["last_work_date"].isoformat() if r["last_work_date"] else None,
                "deadline": r["deadline"].isoformat() if r["deadline"] else None,
                "amount_total": str(r["amount"].quantize(Decimal("0.01"))),
            })
        return sorted(rows, key=lambda r: r["object"])

    def _equipment_act_rows(self, request):
        rows = []
        for wd in self._filtered_workdays(request):
            morning = (
                EquipmentChecklist.objects
                .filter(workday=wd, checklist_type="morning")
                .prefetch_related("items")
                .first()
            )
            evening = (
                EquipmentChecklist.objects
                .filter(workday=wd, checklist_type="evening")
                .prefetch_related("items")
                .first()
            )
            morning_items = {item.name: item.status for item in (morning.items.all() if morning else [])}
            evening_items = {item.name: item.status for item in (evening.items.all() if evening else [])}

            for name in sorted(set(morning_items) | set(evening_items)):
                rows.append(
                    {
                        "workday_id": wd.id,
                        "date": wd.date.isoformat(),
                        "brigade": wd.brigade.name,
                        "item_name": name,
                        "morning_status": morning_items.get(name),
                        "evening_status": evening_items.get(name),
                        "is_mismatch": morning_items.get(name) != evening_items.get(name),
                    }
                )
        return rows

    @action(detail=False, methods=["get"], url_path="timesheet")
    def timesheet(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        return Response({"rows": self._timesheet_rows(request)})

    @action(detail=False, methods=["get"], url_path="piecework")
    def piecework(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._piecework_rows(request)
        total_amount = sum((Decimal(row["amount"]) for row in rows), Decimal("0.00"))
        return Response({"rows": rows, "total_amount": str(total_amount.quantize(Decimal("0.01")))})

    @action(detail=False, methods=["get"], url_path="completion-act")
    def completion_act(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._completion_act_rows(request)
        total_amount = sum((Decimal(row["amount"]) for row in rows), Decimal("0.00"))
        return Response({"rows": rows, "total_amount": str(total_amount.quantize(Decimal("0.01")))})

    @action(detail=False, methods=["get"], url_path="kpi")
    def kpi(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        return Response({"rows": self._kpi_rows(request)})

    @action(detail=False, methods=["get"], url_path="object-time")
    def object_time(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._object_time_rows(request)
        total_hours = sum((Decimal(r["session_hours"]) for r in rows), Decimal("0.00"))
        total_amount = sum((Decimal(r["amount_total"]) for r in rows), Decimal("0.00"))
        return Response({
            "rows": rows,
            "total_hours": str(total_hours.quantize(Decimal("0.01"))),
            "total_amount": str(total_amount.quantize(Decimal("0.01"))),
        })

    @action(detail=False, methods=["get"], url_path="ks2")
    def ks2(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._ks2_rows(request)
        total_amount = sum((Decimal(r["amount"]) for r in rows), Decimal("0.00"))
        return Response({"rows": rows, "total_amount": str(total_amount.quantize(Decimal("0.01")))})

    @action(detail=False, methods=["get"], url_path="ks3")
    def ks3(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._ks3_rows(request)
        return Response({
            "rows": rows,
            "total_period": str(sum((Decimal(r["amount_period"]) for r in rows), Decimal("0.00")).quantize(Decimal("0.01"))),
            "total_year": str(sum((Decimal(r["amount_year"]) for r in rows), Decimal("0.00")).quantize(Decimal("0.01"))),
        })

    @action(detail=False, methods=["get"], url_path="ks11")
    def ks11(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._ks11_rows(request)
        return Response({
            "rows": rows,
            "total_amount": str(sum((Decimal(r["amount_total"]) for r in rows), Decimal("0.00")).quantize(Decimal("0.01"))),
        })

    @action(detail=False, methods=["get"], url_path="equipment-act")
    def equipment_act(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied
        rows = self._equipment_act_rows(request)
        mismatch_count = sum(1 for row in rows if row["is_mismatch"])
        return Response({"rows": rows, "mismatch_count": mismatch_count})

    @action(detail=False, methods=["get"], url_path="filters")
    def filters(self, request):
        denied = self._ensure_report_access(request)
        if denied:
            return denied

        brigades = (
            Brigade.objects.filter(workdays__isnull=False)
            .distinct()
            .order_by("name")
        )
        objects = (
            ProjectObject.objects.filter(work_sessions__isnull=False)
            .distinct()
            .order_by("name")
        )

        return Response(
            {
                "brigades": [
                    {"id": b.id, "name": b.name}
                    for b in brigades
                ],
                "objects": [
                    {"id": obj.id, "name": obj.name}
                    for obj in objects
                ],
            }
        )

    @action(detail=False, methods=["get"], url_path="export/(?P<export_format>[^/.]+)")
    def export(self, request, export_format=None):
        denied = self._ensure_report_access(request)
        if denied:
            return denied

        report_type = request.query_params.get("report", "timesheet")
        report_map = {
            "timesheet": self._timesheet_rows,
            "piecework": self._piecework_rows,
            "completion_act": self._completion_act_rows,
            "equipment_act": self._equipment_act_rows,
            "kpi": self._kpi_rows,
            "object_time": self._object_time_rows,
            "ks2": self._ks2_rows,
            "ks3": self._ks3_rows,
            "ks11": self._ks11_rows,
        }
        builder = report_map.get(report_type)
        if not builder:
            return Response(
                {"error": "Неизвестный тип отчёта. Доступно: timesheet, piecework, completion_act, equipment_act."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rows = builder(request)
        if export_format == "xlsx":
            buffer = io.StringIO()
            if rows:
                writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            else:
                buffer.write("Нет данных\n")
            response = HttpResponse(
                buffer.getvalue(),
                content_type="text/csv; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{report_type}.csv"'
            return response

        if export_format == "pdf":
            content = [f"Report: {report_type}", f"Generated at: {timezone.now().isoformat()}", ""]
            if not rows:
                content.append("No data for selected period.")
            else:
                preview_rows = rows[:200]
                for idx, row in enumerate(preview_rows, start=1):
                    content.append(f"{idx}. " + "; ".join(f"{k}={v}" for k, v in row.items()))
                if len(rows) > len(preview_rows):
                    content.append(f"... more rows: {len(rows) - len(preview_rows)}")
            payload = self._build_simple_pdf(content)
            response = HttpResponse(payload, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{report_type}.pdf"'
            return response

        return Response({"error": "Поддерживаются форматы: xlsx, pdf."}, status=status.HTTP_400_BAD_REQUEST)


class DashboardViewSet(GenericViewSet):
    """Аналитические дашборды: директор, мастер."""

    parser_classes = (JSONParser,)

    DIRECTOR_ROLES = {
        RoleCode.ADMINISTRATOR,
        RoleCode.DIRECTOR,
        RoleCode.PROJECT_MANAGER,
        RoleCode.SUPPORT_MANAGER,
        RoleCode.ACCOUNTANT,
    }

    def _check_role(self, request, roles):
        if request.user.role not in roles:
            return Response({"detail": "Недостаточно прав."}, status=status.HTTP_403_FORBIDDEN)
        return None

    @staticmethod
    def _wd_amount(wd):
        total = Decimal("0")
        for s in wd.sessions.all():
            for w in s.completed_works.all():
                if w.status != WorkStatus.COMPLETED:
                    continue
                rate = w.price_list_item.base_rate or Decimal("0")
                total += w.volume * rate
        return total

    @staticmethod
    def _wd_hours(wd):
        if wd.clock_in_at and wd.clock_out_at:
            return Decimal((wd.clock_out_at - wd.clock_in_at).total_seconds() / 3600)
        return Decimal("0")

    # --- Дашборд директора ---
    @action(detail=False, methods=["get"], url_path="director")
    def director(self, request):
        denied = self._check_role(request, self.DIRECTOR_ROLES)
        if denied:
            return denied

        from collections import defaultdict
        from datetime import timedelta

        today = timezone.localdate()
        week_start = today - timedelta(days=6)
        month_start = today.replace(day=1)

        wd_qs = (
            WorkDay.objects.select_related("brigade", "foreman")
            .prefetch_related(
                "workers_present", "sessions__project_object",
                "sessions__completed_works__price_list_item",
            )
        )

        today_wds = list(wd_qs.filter(date=today))
        week_wds = list(wd_qs.filter(date__gte=week_start, date__lte=today))
        month_wds = list(wd_qs.filter(date__gte=month_start, date__lte=today))

        active_sessions = ObjectSession.objects.filter(
            workday__status=WorkDayStatus.OPEN,
            departed_at__isnull=True,
        ).select_related("project_object", "workday__brigade")

        active_locations = []
        for s in active_sessions:
            duration_min = int((timezone.now() - s.arrived_at).total_seconds() / 60)
            active_locations.append({
                "session_id": s.id,
                "brigade": s.workday.brigade.name,
                "object_id": s.project_object_id,
                "object_name": s.project_object.name,
                "latitude": str(s.project_object.latitude) if s.project_object.latitude else None,
                "longitude": str(s.project_object.longitude) if s.project_object.longitude else None,
                "arrived_at": s.arrived_at.isoformat(),
                "duration_minutes": duration_min,
            })

        # Топ бригад за месяц
        brigade_stats = defaultdict(lambda: {"name": "", "amount": Decimal("0"), "hours": Decimal("0")})
        for wd in month_wds:
            row = brigade_stats[wd.brigade_id]
            row["name"] = wd.brigade.name
            row["amount"] += self._wd_amount(wd)
            row["hours"] += self._wd_hours(wd)
        top_brigades = sorted(
            ({"brigade": v["name"], "amount": str(v["amount"].quantize(Decimal("0.01"))),
              "hours": str(v["hours"].quantize(Decimal("0.01")))} for v in brigade_stats.values()),
            key=lambda x: float(x["amount"]), reverse=True,
        )[:10]

        # Топ монтажников за месяц
        worker_stats = defaultdict(lambda: {"name": "", "amount": Decimal("0"), "days": set()})
        for wd in month_wds:
            members = list(wd.workers_present.all())
            if not members:
                continue
            per = self._wd_amount(wd) / len(members)
            for m in members:
                w = worker_stats[m.id]
                w["name"] = m.get_full_name() or m.username
                w["amount"] += per
                w["days"].add(wd.date)
        top_workers = sorted(
            ({"user": v["name"], "amount": str(v["amount"].quantize(Decimal("0.01"))), "days": len(v["days"])}
             for v in worker_stats.values()),
            key=lambda x: float(x["amount"]), reverse=True,
        )[:10]

        overdue = (
            ProjectObject.objects.filter(
                deadline__lt=today, is_archived=False,
            ).exclude(
                construction_status__in=("completed", "completed_paid"),
            ).order_by("deadline")[:20]
        )
        overdue_list = [
            {
                "object_id": o.id, "name": o.name,
                "deadline": o.deadline.isoformat() if o.deadline else None,
                "days_overdue": (today - o.deadline).days if o.deadline else None,
            }
            for o in overdue
        ]

        def aggregate(wds):
            return {
                "workdays": len(wds),
                "amount": str(sum((self._wd_amount(w) for w in wds), Decimal("0")).quantize(Decimal("0.01"))),
                "hours": str(sum((self._wd_hours(w) for w in wds), Decimal("0")).quantize(Decimal("0.01"))),
            }

        # Дневная динамика за последние 7 дней
        by_day = defaultdict(lambda: Decimal("0"))
        for wd in week_wds:
            by_day[wd.date] += self._wd_amount(wd)
        week_chart = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            week_chart.append({"date": d.isoformat(), "amount": str(by_day[d].quantize(Decimal("0.01")))})

        return Response({
            "today": {
                "date": today.isoformat(),
                "active_brigades": len({wd.brigade_id for wd in today_wds}),
                "active_sessions": len(active_locations),
                **aggregate(today_wds),
            },
            "week": aggregate(week_wds),
            "month": aggregate(month_wds),
            "active_locations": active_locations,
            "top_brigades": top_brigades,
            "top_workers": top_workers,
            "overdue_objects": overdue_list,
            "week_chart": week_chart,
        })

    # --- Прогресс объекта (План/Факт/Прогноз) ---
    @action(detail=False, methods=["get"], url_path="object-progress/(?P<object_id>[0-9]+)")
    def object_progress(self, request, object_id=None):
        denied = self._check_role(request, self.DIRECTOR_ROLES | {RoleCode.FOREMAN})
        if denied:
            return denied

        from collections import defaultdict
        from datetime import timedelta
        from apps.objects.models import ObjectWorkPlan

        obj = ProjectObject.objects.filter(pk=object_id).first()
        if not obj:
            return Response({"error": "Объект не найден."}, status=status.HTTP_404_NOT_FOUND)

        plans = list(
            ObjectWorkPlan.objects.filter(project_object=obj)
            .select_related("work_type")
            .prefetch_related("work_type__items")
        )

        facts_qs = CompletedWork.objects.filter(
            object_session__project_object=obj,
            status=WorkStatus.COMPLETED,
        ).select_related("price_list_item", "object_session", "object_session__workday")

        fact_volume_by_type = defaultdict(lambda: Decimal("0"))
        fact_amount_by_type = defaultdict(lambda: Decimal("0"))
        fact_amount_by_date = defaultdict(lambda: Decimal("0"))
        first_fact_date = None
        last_fact_date = None
        for w in facts_qs:
            wt_id = w.price_list_item.work_type_id
            rate = w.price_list_item.base_rate or Decimal("0")
            amount = w.volume * rate
            fact_volume_by_type[wt_id] += w.volume
            fact_amount_by_type[wt_id] += amount
            d = w.object_session.workday.date
            fact_amount_by_date[d] += amount
            if first_fact_date is None or d < first_fact_date:
                first_fact_date = d
            if last_fact_date is None or d > last_fact_date:
                last_fact_date = d

        today = timezone.localdate()

        def avg_rate(wt):
            rates = [it.base_rate for it in wt.items.all() if it.base_rate]
            return sum(rates, Decimal("0")) / len(rates) if rates else Decimal("0")

        plan_rows = []
        total_planned_amount = Decimal("0")
        total_completed_amount = Decimal("0")
        for p in plans:
            wt = p.work_type
            planned_volume = Decimal(p.planned_volume)
            completed_volume = fact_volume_by_type.get(wt.id, Decimal("0"))
            completed_amount = fact_amount_by_type.get(wt.id, Decimal("0"))
            avg = avg_rate(wt)
            planned_amount = (planned_volume * avg).quantize(Decimal("0.01"))
            total_planned_amount += planned_amount
            total_completed_amount += completed_amount

            percent = (completed_volume / planned_volume * 100) if planned_volume > 0 else Decimal("0")
            percent = min(percent, Decimal("999")).quantize(Decimal("0.1"))
            remaining = max(planned_volume - completed_volume, Decimal("0"))

            forecast_end = None
            historical_daily = Decimal("0")
            if p.planned_start and (today - p.planned_start).days > 0:
                days_elapsed = (today - p.planned_start).days
                historical_daily = (completed_volume / days_elapsed).quantize(Decimal("0.001")) if days_elapsed > 0 else Decimal("0")
                if remaining > 0 and historical_daily > 0:
                    days_left = int((remaining / historical_daily).to_integral_value(rounding="ROUND_CEILING"))
                    forecast_end = (today + timedelta(days=days_left)).isoformat()

            # Требуемая дневная выработка для попадания в дедлайн
            required_daily = Decimal("0")
            target_end = p.planned_end or obj.deadline
            if target_end and remaining > 0:
                days_left_to_deadline = (target_end - today).days
                if days_left_to_deadline > 0:
                    required_daily = (remaining / Decimal(days_left_to_deadline)).quantize(Decimal("0.001"))
                else:
                    required_daily = remaining  # уже просрочено

            risk_required = "green"
            if required_daily > 0 and historical_daily > 0:
                if required_daily > historical_daily * Decimal("1.5"):
                    risk_required = "red"
                elif required_daily > historical_daily:
                    risk_required = "yellow"
            elif required_daily > 0 and historical_daily == 0 and completed_volume == 0:
                risk_required = "yellow"

            risk = "green"
            if p.planned_end and p.planned_end < today and percent < Decimal("100"):
                risk = "red"
            elif p.planned_end and forecast_end and forecast_end > p.planned_end.isoformat():
                risk = "yellow"
            elif not p.planned_end:
                if percent < Decimal("40"):
                    risk = "yellow"
                if percent < Decimal("10") and completed_volume == 0:
                    risk = "red"

            plan_rows.append({
                "plan_id": p.id,
                "work_type_id": wt.id,
                "work_type_name": wt.name,
                "planned_volume": str(planned_volume),
                "completed_volume": str(completed_volume),
                "remaining_volume": str(remaining),
                "percent": str(percent),
                "planned_start": p.planned_start.isoformat() if p.planned_start else None,
                "planned_end": p.planned_end.isoformat() if p.planned_end else None,
                "forecast_end": forecast_end,
                "planned_amount": str(planned_amount),
                "completed_amount": str(completed_amount.quantize(Decimal("0.01"))),
                "risk": risk,
                "required_daily": str(required_daily),
                "historical_daily": str(historical_daily),
                "risk_required": risk_required,
                "notes": p.notes,
            })

        # S-кривая по сумме (план линейный по датам, факт нарастающим итогом)
        plan_starts = [p.planned_start for p in plans if p.planned_start]
        plan_ends = [p.planned_end for p in plans if p.planned_end]
        period_start = min(plan_starts) if plan_starts else first_fact_date
        period_end_candidates = list(plan_ends)
        if last_fact_date:
            period_end_candidates.append(last_fact_date)
        period_end = max(period_end_candidates) if period_end_candidates else None
        if period_end and period_end < today:
            period_end = today

        s_curve = []
        if period_start and period_end and period_end >= period_start:
            day_count = (period_end - period_start).days + 1
            step = max(1, day_count // 60)
            d = period_start
            while d <= period_end:
                planned_to_d = Decimal("0")
                for p in plans:
                    if not p.planned_start or not p.planned_end or p.planned_end < p.planned_start:
                        continue
                    avg = avg_rate(p.work_type)
                    pa = Decimal(p.planned_volume) * avg
                    if d >= p.planned_end:
                        planned_to_d += pa
                    elif d >= p.planned_start:
                        days = (p.planned_end - p.planned_start).days
                        passed = (d - p.planned_start).days
                        if days > 0:
                            planned_to_d += pa * Decimal(passed) / Decimal(days)
                actual_to_d = sum(
                    (amount for dd, amount in fact_amount_by_date.items() if dd <= d),
                    Decimal("0"),
                )
                s_curve.append({
                    "date": d.isoformat(),
                    "planned": str(planned_to_d.quantize(Decimal("0.01"))),
                    "actual": str(actual_to_d.quantize(Decimal("0.01"))),
                })
                d = d + timedelta(days=step)

        total_percent = (
            (total_completed_amount / total_planned_amount * 100).quantize(Decimal("0.1"))
            if total_planned_amount > 0 else Decimal("0.0")
        )

        return Response({
            "object": {
                "id": obj.id, "name": obj.name,
                "deadline": obj.deadline.isoformat() if obj.deadline else None,
            },
            "totals": {
                "planned_amount": str(total_planned_amount.quantize(Decimal("0.01"))),
                "completed_amount": str(total_completed_amount.quantize(Decimal("0.01"))),
                "percent": str(total_percent),
                "today": today.isoformat(),
            },
            "plans": plan_rows,
            "s_curve": s_curve,
        })

    # --- Список объектов с планом (для навигации с дашборда) ---
    @action(detail=False, methods=["get"], url_path="objects-with-plans")
    def objects_with_plans(self, request):
        from django.db.models import Sum
        denied = self._check_role(request, self.DIRECTOR_ROLES | {RoleCode.FOREMAN})
        if denied:
            return denied
        from apps.objects.models import ObjectWorkPlan
        objs = (
            ProjectObject.objects.filter(work_plans__isnull=False, is_archived=False)
            .distinct().order_by("name")
        )
        result = []
        for obj in objs:
            plans = ObjectWorkPlan.objects.filter(project_object=obj)
            planned_volume = sum((Decimal(p.planned_volume) for p in plans), Decimal("0"))
            wt_ids = [p.work_type_id for p in plans]
            completed_volume = CompletedWork.objects.filter(
                object_session__project_object=obj, status=WorkStatus.COMPLETED,
                price_list_item__work_type_id__in=wt_ids,
            ).aggregate(total=Sum("volume"))["total"] or Decimal("0")
            percent = (
                (Decimal(completed_volume) / planned_volume * 100).quantize(Decimal("0.1"))
                if planned_volume > 0 else Decimal("0.0")
            )
            result.append({
                "id": obj.id, "name": obj.name,
                "deadline": obj.deadline.isoformat() if obj.deadline else None,
                "plans_count": plans.count(),
                "percent": str(min(percent, Decimal("999"))),
            })
        return Response(result)

    # --- Дашборд мастера ---
    @action(detail=False, methods=["get"], url_path="master")
    def master(self, request):
        denied = self._check_role(request, {RoleCode.FOREMAN})
        if denied:
            return denied

        from collections import defaultdict
        from datetime import timedelta

        brigade = request.user.foreman_brigades.first()
        if not brigade:
            return Response({"error": "У вас нет назначенной бригады."}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.localdate()
        week_start = today - timedelta(days=6)
        month_start = today.replace(day=1)

        wd_qs = (
            WorkDay.objects.filter(brigade=brigade)
            .prefetch_related("sessions__completed_works__price_list_item", "sessions__project_object")
        )
        today_wd = wd_qs.filter(date=today).first()
        month_wds = list(wd_qs.filter(date__gte=month_start, date__lte=today))
        week_wds = list(wd_qs.filter(date__gte=week_start, date__lte=today))

        # Сегодня
        today_payload = None
        current_session = None
        if today_wd:
            sessions = list(today_wd.sessions.all())
            completed_works_count = 0
            for s in sessions:
                completed_works_count += sum(1 for w in s.completed_works.all() if w.status == WorkStatus.COMPLETED)
            for s in sessions:
                if s.departed_at is None:
                    current_session = {
                        "session_id": s.id,
                        "object_name": s.project_object.name,
                        "arrived_at": s.arrived_at.isoformat(),
                    }
                    break
            today_payload = {
                "workday_id": today_wd.id,
                "clock_in_at": today_wd.clock_in_at.isoformat() if today_wd.clock_in_at else None,
                "clock_out_at": today_wd.clock_out_at.isoformat() if today_wd.clock_out_at else None,
                "sessions": len(sessions),
                "completed_works": completed_works_count,
                "amount": str(self._wd_amount(today_wd).quantize(Decimal("0.01"))),
                "hours": str(self._wd_hours(today_wd).quantize(Decimal("0.01"))),
            }

        # Активные назначения, выданные мастером
        active_assignments = CompletedWork.objects.filter(
            assigned_by=request.user,
            status__in=(WorkStatus.ASSIGNED, WorkStatus.IN_PROGRESS),
            object_session__workday__status=WorkDayStatus.OPEN,
        ).count()

        # Чек-листы сегодня
        morning = EquipmentChecklist.objects.filter(workday=today_wd, checklist_type="morning").exists() if today_wd else False
        evening = EquipmentChecklist.objects.filter(workday=today_wd, checklist_type="evening").exists() if today_wd else False

        # Дневной график за неделю
        by_day = defaultdict(lambda: Decimal("0"))
        for wd in week_wds:
            by_day[wd.date] += self._wd_amount(wd)
        week_chart = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            week_chart.append({"date": d.isoformat(), "amount": str(by_day[d].quantize(Decimal("0.01")))})

        # Месячный итог
        month_amount = sum((self._wd_amount(wd) for wd in month_wds), Decimal("0"))
        month_hours = sum((self._wd_hours(wd) for wd in month_wds), Decimal("0"))

        return Response({
            "brigade": {
                "id": brigade.id,
                "name": brigade.name,
                "members_count": brigade.members.count(),
            },
            "today": today_payload,
            "current_session": current_session,
            "active_assignments": active_assignments,
            "checklists_today": {"morning": morning, "evening": evening},
            "week_chart": week_chart,
            "month": {
                "workdays": len(month_wds),
                "amount": str(month_amount.quantize(Decimal("0.01"))),
                "hours": str(month_hours.quantize(Decimal("0.01"))),
            },
        })

    # --- Дашборд РП ---
    @action(detail=False, methods=["get"], url_path="pm")
    def pm(self, request):
        denied = self._check_role(
            request,
            {RoleCode.PROJECT_MANAGER, RoleCode.ADMINISTRATOR, RoleCode.DIRECTOR},
        )
        if denied:
            return denied

        from collections import defaultdict
        from datetime import timedelta
        from django.db.models import Sum
        from apps.objects.models import ObjectWorkPlan

        today = timezone.localdate()
        month_start = today.replace(day=1)

        # «Мои объекты»: для PROJECT_MANAGER — где project_manager = user;
        # для ADMIN/DIRECTOR — все.
        my_objects_qs = ProjectObject.objects.filter(is_archived=False)
        if request.user.role == RoleCode.PROJECT_MANAGER:
            my_objects_qs = my_objects_qs.filter(project_manager=request.user)
        my_objects = list(my_objects_qs.order_by("name"))
        my_object_ids = [o.id for o in my_objects]

        # Прогресс по объектам с планами
        plans_by_obj = defaultdict(list)
        for p in ObjectWorkPlan.objects.filter(project_object_id__in=my_object_ids).select_related("work_type"):
            plans_by_obj[p.project_object_id].append(p)

        completed_by_obj = defaultdict(lambda: Decimal("0"))
        completed_amount_by_obj = defaultdict(lambda: Decimal("0"))
        for w in (
            CompletedWork.objects.filter(
                object_session__project_object_id__in=my_object_ids,
                status=WorkStatus.COMPLETED,
            )
            .select_related("price_list_item", "object_session")
        ):
            obj_id = w.object_session.project_object_id
            completed_by_obj[obj_id] += w.volume
            rate = w.price_list_item.base_rate or Decimal("0")
            completed_amount_by_obj[obj_id] += w.volume * rate

        progress_rows = []
        problem_zones = []
        for obj in my_objects:
            plans = plans_by_obj.get(obj.id, [])
            planned_volume = sum((Decimal(p.planned_volume) for p in plans), Decimal("0"))
            done_volume = completed_by_obj.get(obj.id, Decimal("0"))
            percent = (
                (done_volume / planned_volume * 100).quantize(Decimal("0.1"))
                if planned_volume > 0 else Decimal("0.0")
            )
            row = {
                "id": obj.id, "name": obj.name,
                "deadline": obj.deadline.isoformat() if obj.deadline else None,
                "planned_volume": str(planned_volume),
                "completed_volume": str(done_volume),
                "completed_amount": str(completed_amount_by_obj.get(obj.id, Decimal("0")).quantize(Decimal("0.01"))),
                "percent": str(min(percent, Decimal("999"))),
                "plans_count": len(plans),
            }
            progress_rows.append(row)

            # Проблемные зоны
            issue = None
            if obj.deadline and obj.deadline < today and percent < Decimal("100"):
                issue = {"object_id": obj.id, "name": obj.name, "type": "overdue",
                         "message": f"Просрочено на {(today - obj.deadline).days} дн., прогресс {percent}%"}
            elif obj.deadline and (obj.deadline - today).days <= 14 and percent < Decimal("60"):
                issue = {"object_id": obj.id, "name": obj.name, "type": "at_risk",
                         "message": f"До дедлайна {(obj.deadline - today).days} дн., прогресс {percent}%"}
            if issue:
                problem_zones.append(issue)

        # План-факт по бригадам, работающим на моих объектах за месяц
        wd_qs = (
            WorkDay.objects.filter(
                date__gte=month_start, date__lte=today,
                sessions__project_object_id__in=my_object_ids,
            )
            .select_related("brigade")
            .prefetch_related("sessions__completed_works__price_list_item", "sessions__project_object")
            .distinct()
        )
        brigade_stats = defaultdict(lambda: {"name": "", "amount": Decimal("0"), "hours": Decimal("0"), "workdays": 0})
        for wd in wd_qs:
            row = brigade_stats[wd.brigade_id]
            row["name"] = wd.brigade.name
            row["workdays"] += 1
            row["hours"] += self._wd_hours(wd)
            for s in wd.sessions.all():
                if s.project_object_id not in my_object_ids:
                    continue
                for w in s.completed_works.all():
                    if w.status != WorkStatus.COMPLETED:
                        continue
                    rate = w.price_list_item.base_rate or Decimal("0")
                    row["amount"] += w.volume * rate
        top_brigades = sorted(
            ({"brigade": v["name"], "amount": str(v["amount"].quantize(Decimal("0.01"))),
              "hours": str(v["hours"].quantize(Decimal("0.01"))),
              "workdays": v["workdays"]} for v in brigade_stats.values()),
            key=lambda x: float(x["amount"]), reverse=True,
        )

        # Сейчас на моих объектах
        active_sessions = ObjectSession.objects.filter(
            workday__status=WorkDayStatus.OPEN,
            departed_at__isnull=True,
            project_object_id__in=my_object_ids,
        ).select_related("project_object", "workday__brigade")
        active_locations = []
        for s in active_sessions:
            duration_min = int((timezone.now() - s.arrived_at).total_seconds() / 60)
            active_locations.append({
                "session_id": s.id,
                "brigade": s.workday.brigade.name,
                "object_id": s.project_object_id,
                "object_name": s.project_object.name,
                "arrived_at": s.arrived_at.isoformat(),
                "duration_minutes": duration_min,
            })

        return Response({
            "my_objects_count": len(my_objects),
            "active_sessions": len(active_locations),
            "problem_zones": problem_zones,
            "progress": sorted(progress_rows, key=lambda x: -float(x["percent"])),
            "top_brigades": top_brigades,
            "active_locations": active_locations,
            "month_amount": str(sum((Decimal(b["amount"]) for b in top_brigades), Decimal("0")).quantize(Decimal("0.01"))),
        })
