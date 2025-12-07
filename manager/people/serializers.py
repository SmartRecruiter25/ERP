from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers

from hr.employees.models import Employee, EmployeeStatus
from hr.org_structure.models import Department, JobTitle
from hr.ess.models import LeaveStatus


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    department = serializers.CharField(source="department.name", read_only=True)
    position = serializers.CharField(source="job_title.title_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_code",
            "full_name",
            "department",
            "position",
            "email",
            "status_display",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_status_display(self, obj):
        today = self.context.get("today")
        if today is None:
            today = timezone.now().date()

        has_leave_today = obj.leave_requests.filter(
            status=LeaveStatus.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
        ).exists()

        if has_leave_today:
            return "On Leave"

        return obj.get_status_display()


class PeopleHubSummarySerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    on_leave_today = serializers.IntegerField()
    departments_count = serializers.IntegerField()


class EmployeeCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()

    job_title = serializers.PrimaryKeyRelatedField(
        queryset=JobTitle.objects.all(),
        required=False,
        allow_null=True,
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )

    start_date = serializers.DateField()

    status = serializers.ChoiceField(
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.ACTIVE,
    )

    def validate_email(self, value):
        User = get_user_model()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def validate_full_name(self, value):
        return value.strip()