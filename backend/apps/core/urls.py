from rest_framework.routers import DefaultRouter

from .views import BusinessViewSet, RoleViewSet, UserViewSet

router = DefaultRouter()
router.register("businesses", BusinessViewSet, basename="business")
router.register("roles", RoleViewSet, basename="role")
router.register("users", UserViewSet, basename="user")

urlpatterns = router.urls
