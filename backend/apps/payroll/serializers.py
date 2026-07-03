from rest_framework import serializers

from .models import Employee, PayrollItem, PayrollRun, SalaryScheme


class EmployeeSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name", read_only=True, default=None
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "full_name",
            "business",
            "business_name",
            "position",
            "salary_type",
            "is_salesperson",
            "is_active",
        ]


class SalarySchemeSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = SalaryScheme
        fields = ["id", "employee", "employee_name", "scheme_type", "config", "is_active"]

    def validate(self, attrs):
        scheme_type = attrs.get("scheme_type", getattr(self.instance, "scheme_type", None))
        config = attrs.get("config", getattr(self.instance, "config", {})) or {}
        if scheme_type == SalaryScheme.SchemeType.PER_UNIT_TIERED:
            tiers = config.get("tiers")
            if not tiers:
                raise serializers.ValidationError({"config": "tiers обязателен"})
            if config.get("tier_mode") not in ("flat", "marginal"):
                raise serializers.ValidationError(
                    {"config": "tier_mode должен быть flat или marginal"}
                )
        if scheme_type == SalaryScheme.SchemeType.PERCENT_OF_SALES:
            if "percent" not in config:
                raise serializers.ValidationError({"config": "percent обязателен"})
        return attrs


class PayrollItemSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    business_name = serializers.CharField(
        source="employee.business.name", read_only=True, default=None
    )
    salary_type = serializers.CharField(source="employee.salary_type", read_only=True)

    class Meta:
        model = PayrollItem
        fields = [
            "id",
            "employee",
            "employee_name",
            "business_name",
            "salary_type",
            "base",
            "bonus",
            "total",
            "breakdown",
        ]
        read_only_fields = fields


class PayrollRunSerializer(serializers.ModelSerializer):
    total_fund = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "year",
            "month",
            "status",
            "paid_from_hq",
            "created_by",
            "created_at",
            "finalized_at",
            "total_fund",
            "items_count",
        ]
        read_only_fields = fields

    def get_total_fund(self, obj) -> str:
        from . import selectors

        return str(selectors.run_total(obj))


class PayrollRunDetailSerializer(PayrollRunSerializer):
    items = PayrollItemSerializer(many=True, read_only=True)

    class Meta(PayrollRunSerializer.Meta):
        fields = PayrollRunSerializer.Meta.fields + ["items"]
        read_only_fields = fields


class RunPayrollSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    inputs = serializers.DictField(required=False, default=dict)
