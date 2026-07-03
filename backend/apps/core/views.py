from rest_framework import viewsets

from .models import Business, Role, User
from .permissions import BusinessesSection, CanViewUsers
from .serializers import BusinessSerializer, RoleSerializer, UserListSerializer


class BusinessViewSet(viewsets.ModelViewSet):
    """Бизнесы холдинга: чтение — всем ролям, CRUD — владельцу (Часть 0)."""

    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [BusinessesSection]
    pagination_class = None
    filterset_fields = ["kind", "is_active"]

    def perform_destroy(self, instance):
        # Бизнесы не удаляем физически — деактивируем.
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """Справочник ролей холдинга (data-driven, Часть 0)."""

    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [CanViewUsers]
    pagination_class = None


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Список пользователей холдинга (Часть 0)."""

    queryset = User.objects.select_related("business").filter(is_active=True)
    serializer_class = UserListSerializer
    permission_classes = [CanViewUsers]
    filterset_fields = ["role", "business"]
    search_fields = ["full_name", "email"]
