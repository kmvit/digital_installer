from rest_framework import viewsets

from apps.users.permissions import IsAdminScope

from .models import ProjectObject
from .serializers import ProjectObjectSerializer


class ProjectObjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectObjectSerializer
    permission_classes = [IsAdminScope]

    def get_queryset(self):
        queryset = ProjectObject.objects.select_related("price_list")
        price_list_id = self.request.query_params.get("price_list")
        if price_list_id:
            queryset = queryset.filter(price_list_id=price_list_id)
        return queryset
