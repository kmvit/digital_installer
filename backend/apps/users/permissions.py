from rest_framework.permissions import BasePermission

from .models import RoleCode


class IsDirectorOrProjectManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.roles.filter(
                code__in=[
                    RoleCode.ADMINISTRATOR,
                    RoleCode.DIRECTOR,
                    RoleCode.PROJECT_MANAGER,
                ]
            ).exists()
        )
