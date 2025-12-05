from datetime import datetime

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from manager.attendance.serializers import (
    AttendanceRecordSerializer,
    AttendanceSummarySerializer,
    AttendanceEmployeeSerializer,
)

from hr.attendance.models import AttendanceRecord, AttendanceStatus
from hr.employees.models import Employee, EmployeeStatus
from hr.org_structure.models import Company


class BaseCompanyMixin:
    def get_company(self, request):
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None:
            return employee_profile.company
        return Company.objects.first()

    def get_date_from_query(self, request, param_name: str = "date"):

        date_str = request.query_params.get(param_name)
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return None
        return timezone.now().date()


class AttendanceListView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            return Response(
                {"date": timezone.now().date().isoformat(), "records": []}, status=200
            )

        date = self.get_date_from_query(request, "date")
        if date is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400
            )

        qs = AttendanceRecord.objects.filter(
            employee__company=company,
            date=date,
        ).select_related(
            "employee__user",
            "employee__department",
            "employee__job_title",
            "shift",
        )

        employee_param = request.query_params.get("employee")

        if employee_param and employee_param != "all":
            qs = qs.filter(employee_id=employee_param)

        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)

        qs = qs.order_by("employee__user__first_name", "employee__user__last_name")

        serializer = AttendanceRecordSerializer(qs, many=True)

        data = {
            "date": date.isoformat(),
            "records": serializer.data,
        }
        return Response(data)


class AttendanceSummaryView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = self.get_company(request)
        today = timezone.now().date()

        if not company:
            data = {
                "date": today,
                "present": 0,
                "absent": 0,
                "on_leave": 0,
                "remote": 0,
                "late": 0,
            }
            serializer = AttendanceSummarySerializer(data)
            return Response(serializer.data)

        date = BaseCompanyMixin.get_date_from_query(self, request, "date")
        if date is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400
            )

        qs = AttendanceRecord.objects.filter(
            employee__company=company,
            date=date,
        )

        present = qs.filter(status=AttendanceStatus.PRESENT).count()
        absent = qs.filter(status=AttendanceStatus.ABSENT).count()
        on_leave = qs.filter(status=AttendanceStatus.ON_LEAVE).count()
        remote = qs.filter(status=AttendanceStatus.REMOTE).count()
        late = qs.filter(status=AttendanceStatus.LATE).count()

        data = {
            "date": date,
            "present": present,
            "absent": absent,
            "on_leave": on_leave,
            "remote": remote,
            "late": late,
        }

        serializer = AttendanceSummarySerializer(data)
        return Response(serializer.data)


class AttendanceEmployeesFilterView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            return Response([], status=200)

        qs = (
            Employee.objects.filter(
                company=company,
                status=EmployeeStatus.ACTIVE,
            )
            .select_related("user", "department", "job_title")
            .order_by("user__first_name", "user__last_name")
        )

        serializer = AttendanceEmployeeSerializer(qs, many=True)
        return Response(serializer.data)