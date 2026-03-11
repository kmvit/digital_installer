from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Brigade, User
from .permissions import IsAdminScope
from .serializers import BrigadeSerializer, CurrentUserSerializer, UserAdminSerializer


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)


class UserAdminViewSet(viewsets.ModelViewSet):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminScope]

    def get_queryset(self):
        queryset = User.objects.order_by("id")
        status_value = self.request.query_params.get("status")
        role_code = self.request.query_params.get("role")
        search = self.request.query_params.get("search")

        if status_value:
            queryset = queryset.filter(status=status_value)
        if role_code:
            queryset = queryset.filter(role=role_code)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )

        return queryset


class BrigadeViewSet(viewsets.ModelViewSet):
    serializer_class = BrigadeSerializer
    permission_classes = [IsAuthenticated, IsAdminScope]

    def get_queryset(self):
        queryset = Brigade.objects.select_related("foreman").prefetch_related("members")
        active = self.request.query_params.get("active")
        if active is not None:
            active_bool = active.lower() in {"1", "true", "yes"}
            queryset = queryset.filter(is_active=active_bool)
        return queryset
