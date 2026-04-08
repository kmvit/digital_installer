from rest_framework.permissions import BasePermission

from apps.users.models import RoleCode


class IsForeman(BasePermission):
    """Доступ для бригадиров (мастеров)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == RoleCode.FOREMAN
        )


class IsForemanOrWorker(BasePermission):
    """Доступ для бригадиров и монтажников."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (RoleCode.FOREMAN, RoleCode.WORKER)
        )


class IsApprover(BasePermission):
    """Доступ для приёмки отчётов: РП, директор, администратор."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (
                RoleCode.PROJECT_MANAGER,
                RoleCode.DIRECTOR,
                RoleCode.ADMINISTRATOR,
            )
        )


class IsAuthenticated(BasePermission):
    """Любой авторизованный пользователь."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
