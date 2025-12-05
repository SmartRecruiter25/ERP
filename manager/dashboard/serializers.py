from rest_framework import serializers
from hr.org_structure.models import CompanyNews


class CompanyNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyNews
        fields = ["id", "title", "content", "date", "is_pinned"]


class DashboardSummarySerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    active_contracts = serializers.IntegerField()
    pending_leaves = serializers.IntegerField()
    payroll_due = serializers.DecimalField(max_digits=14, decimal_places=2)


    departments_count = serializers.IntegerField()


    news = CompanyNewsSerializer(many=True)

    recent_activity = serializers.ListField(
        child=serializers.CharField(),
    )

class HRDashboardSummarySerializer(serializers.Serializer):

    total_employees = serializers.IntegerField()
    employees_change_percent = serializers.FloatField() 


    open_positions = serializers.IntegerField()
    open_positions_urgent = serializers.IntegerField()  



    pending_leave_requests = serializers.IntegerField()
    pending_leaves_require_approval = serializers.IntegerField() 


    payroll_processed = serializers.DecimalField(max_digits=14, decimal_places=2)
    payroll_currency = serializers.CharField()
    payroll_period_label = serializers.CharField()