import django_filters

from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="occurred_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="occurred_at", lookup_expr="date__lte")

    class Meta:
        model = Transaction
        fields = ["business", "kind", "status", "method", "category", "date_from", "date_to"]
