from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BarterViewSet, DebtViewSet, NetDebtsView, TransferViewSet

router = DefaultRouter()
router.register("transfers", TransferViewSet, basename="transfer")
router.register("debts", DebtViewSet, basename="debt")
router.register("barters", BarterViewSet, basename="barter")

urlpatterns = [
    path("net", NetDebtsView.as_view(), name="net-debts"),
    *router.urls,
]
