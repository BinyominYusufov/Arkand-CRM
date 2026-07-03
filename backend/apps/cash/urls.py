from rest_framework.routers import DefaultRouter

from .views import CashOperationViewSet, CashRegisterViewSet

router = DefaultRouter()
router.register("registers", CashRegisterViewSet, basename="cash-register")
router.register("operations", CashOperationViewSet, basename="cash-operation")

urlpatterns = router.urls
