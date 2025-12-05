from rest_framework import serializers
from hr.contracts.models import EmployeeContract
from django.utils import timezone


class ContractListSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    employee_name = serializers.SerializerMethodField()
    department = serializers.CharField(source="employee.department.name", read_only=True)
    job_title = serializers.CharField(source="employee.job_title.title_name", read_only=True)
    is_active = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeContract
        fields = [
            "id",
            "employee_code",
            "employee_name",
            "department",
            "job_title",
            "contract_type",
            "start_date",
            "end_date",
            "status",
            "is_active",
            "days_to_expiry",
            "base_salary",
            "currency",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username

    def get_is_active(self, obj):
        today = timezone.now().date()
        return obj.start_date <= today <= obj.end_date and obj.status == "active"

    def get_days_to_expiry(self, obj):
        today = timezone.now().date()
        if obj.end_date >= today:
            return (obj.end_date - today).days
        return 0


class ContractsSummarySerializer(serializers.Serializer):
    total_contracts = serializers.IntegerField()
    active_contracts = serializers.IntegerField()
    expiring_30_days = serializers.IntegerField()
    expired_contracts = serializers.IntegerField()