from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminScope

from .models import PriceList, PriceListItem
from .serializers import PriceListItemSerializer, PriceListSerializer


class PriceListViewSet(viewsets.ModelViewSet):
    serializer_class = PriceListSerializer
    permission_classes = [IsAdminScope]

    def get_queryset(self):
        queryset = PriceList.objects.annotate(items_count=Count("items"), objects_count=Count("objects"))
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() in {"1", "true", "yes"})
        return queryset


class PriceListItemViewSet(viewsets.ModelViewSet):
    serializer_class = PriceListItemSerializer
    permission_classes = [IsAdminScope]

    def get_queryset(self):
        queryset = PriceListItem.objects.select_related("price_list")
        price_list_id = self.request.query_params.get("price_list")
        if price_list_id:
            queryset = queryset.filter(price_list_id=price_list_id)
        return queryset


class PriceListImportStubView(APIView):
    permission_classes = [IsAdminScope]

    def post(self, request):
        return Response(
            {"detail": "Импорт расценок временно заглушен до получения шаблона файлов."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class PriceListExportStubView(APIView):
    permission_classes = [IsAdminScope]

    def get(self, request):
        return Response(
            {"detail": "Экспорт расценок временно заглушен до согласования формата."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
