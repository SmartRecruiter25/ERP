from rest_framework import serializers

from hr.attendance.models import AttendanceRecord
from hr.employees.models import Employee


class AttendanceEmployeeSerializer(serializers.ModelSerializer):
    """
    قائمة الموظفين للفلتر (All Employees dropdown)
    """
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Employee
        fields = ["id", "employee_code", "full_name", "email"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """
    صف واحد من جدول Attendance Logs
    """
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(
        source="employee.employee_code",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    # أوقات جاهزة بصيغة HH:MM للواجهة
    check_in_time = serializers.TimeField(
        source="check_in",
        format="%H:%M",
        read_only=True,
        allow_null=True,
    )
    check_out_time = serializers.TimeField(
        source="check_out",
        format="%H:%M",
        read_only=True,
        allow_null=True,
    )

    date_label = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "date",
            "date_label",
            "employee",
            "employee_code",
            "employee_name",
            "check_in",
            "check_in_time",
            "check_out",
            "check_out_time",
            "total_hours",
            "status",
            "status_label",
        ]
        read_only_fields = fields

    def get_employee_name(self, obj):
        user = obj.employee.user
        return user.get_full_name() or user.username

    def get_date_label(self, obj):
        # مثال: Jan 15, 2024
        return obj.date.strftime("%b %d, %Y")
        
class AttendanceSummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    on_leave = serializers.IntegerField()
    remote = serializers.IntegerField()
    late = serializers.IntegerField()