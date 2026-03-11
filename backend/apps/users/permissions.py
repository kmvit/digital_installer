from rest_framework.permissions import BasePermission

from .models import RoleCode


class IsDirectorOrProjectManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role
            in [
                RoleCode.ADMINISTRATOR,
                RoleCode.DIRECTOR,
                RoleCode.PROJECT_MANAGER,
            ]
        )


class IsAdminScope(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in [
            RoleCode.ADMINISTRATOR,
            RoleCode.DIRECTOR,
            RoleCode.PROJECT_MANAGER,
        ]
