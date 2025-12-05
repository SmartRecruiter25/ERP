from rest_framework import serializers
from hr.ess.models import LeaveRequest, LeaveType, LeaveStatus


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    department = serializers.CharField(source="employee.department.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee_code",
            "employee_name",
            "department",
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "reason",
            "status",
            "approver",
            "approved_at",
            "created_at",
        ]
        read_only_fields = ["status", "approver", "approved_at", "created_at"]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class LeaveApproveRejectSerializer(serializers.Serializer):
  
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True)