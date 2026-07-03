from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ExpenseCategoryViewSet, ProfitView, TransactionViewSet

router = DefaultRouter()
router.register("categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("profit", ProfitView.as_view(), name="finance-profit"),
    *router.urls,
]
