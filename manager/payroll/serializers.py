from rest_framework import serializers
from hr.payroll.models import PayrollRun
import calendar
from datetime import date

class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "company",
            "name",
            "year",
            "month",
            "period_start",
            "period_end",
            "status",
            "total_employees",
            "total_gross",
            "total_net",
            "created_at",
            "finalized_at",
        ]
        read_only_fields = fields


class PayrollSummarySerializer(serializers.Serializer):
    total_runs = serializers.IntegerField()
    last_run_total_net = serializers.DecimalField(max_digits=14, decimal_places=2)
    last_run_status = serializers.CharField(allow_null=True)
    last_run_period = serializers.CharField(allow_null=True)
    employees_in_last_run = serializers.IntegerField()
    unpaid_total = serializers.DecimalField(max_digits=14, decimal_places=2)

class PayrollRunCreateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)

    include_bonuses = serializers.BooleanField(required=False, default=False)
    include_overtime = serializers.BooleanField(required=False, default=False)
    include_deductions = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        y = attrs["year"]
        m = attrs["month"]
        last_day = calendar.monthrange(y, m)[1]
        attrs["period_start"] = date(y, m, 1)
        attrs["period_end"] = date(y, m, last_day)
        return attrs