from datetime import datetime
from rest_framework import status
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
import requests

from manager.attendance.serializers import (
    AttendanceRecordSerializer,
    AttendanceSummarySerializer,
    AttendanceEmployeeSerializer,
)
from accounts.permissions import IsAdminOrHR
from hr.attendance.models import AttendanceRecord, AttendanceStatus , EmployeeShiftAssignment
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
    permission_classes = [IsAuthenticated  ,IsAdminOrHR]

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
    permission_classes = [IsAuthenticated , IsAdminOrHR]

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
    permission_classes = [IsAuthenticated , IsAdminOrHR]

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

def get_employee_shift_for_date(employee, day):
    return (
        EmployeeShiftAssignment.objects
        .filter(employee=employee, start_date__lte=day, end_date__gte=day)
        .order_by("-is_primary", "-start_date")
        .first()
    )


def notify_ai(payload: dict):
    # مهم: ما لازم AI يوقف التسجيل
    try:
        requests.post(settings.AI_PUNCH_WEBHOOK_URL, json=payload, timeout=5)
    except Exception:
        pass


class CheckInView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]  # الموظف نفسه لازم يقدر يبصّم

    @transaction.atomic
    def post(self, request):
        company = self.get_company(request)

        employee_id = request.data.get("employee_id")
        if not employee_id:
            return Response({"success": False, "error": "employee_id is required"}, status=400)

        # ✅ تأكد الموظف موجود وبنفس الشركة
        try:
            employee = Employee.objects.select_for_update().get(id=employee_id, company=company)
        except Employee.DoesNotExist:
            return Response({"success": False, "error": "Employee not found in your company."}, status=404)

        now = timezone.now()
        day = timezone.localdate()

        record, created = AttendanceRecord.objects.select_for_update().get_or_create(
            employee=employee,
            date=day,
            defaults={"check_in": now, "status": AttendanceStatus.PRESENT},
        )

        if not created and record.check_in:
            return Response({"success": False, "error": "Already checked in today."}, status=400)

        record.check_in = now

        if not record.shift:
            assign = get_employee_shift_for_date(employee, day)
            if assign:
                record.shift = assign.shift

        record.status = AttendanceStatus.PRESENT
        record.save()

        # ✅ AI بعد الحفظ
        notify_ai({
            "event": "check_in",
            "employee_id": employee.id,
            "attendance_id": record.id,
            "timestamp": record.check_in.isoformat() if record.check_in else None,
            "date": str(record.date),
            "company_id": company.id if company else None,
        })

        return Response({
            "success": True,
            "action": "check_in",
            "attendance_id": record.id,
            "check_in": record.check_in,
            "date": record.date,
        })

class CheckOutView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        company = self.get_company(request)

        employee_id = request.data.get("employee_id")
        if not employee_id:
            return Response({"success": False, "error": "employee_id is required"}, status=400)

        try:
            employee = Employee.objects.select_for_update().get(id=employee_id, company=company)
        except Employee.DoesNotExist:
            return Response({"success": False, "error": "Employee not found in your company."}, status=404)

        now = timezone.now()
        day = timezone.localdate()

        try:
            record = AttendanceRecord.objects.select_for_update().get(employee=employee, date=day)
        except AttendanceRecord.DoesNotExist:
            return Response({"success": False, "error": "No check-in found for today."}, status=400)

        if not record.check_in:
            return Response({"success": False, "error": "No check-in found for today."}, status=400)

        if record.check_out:
            return Response({"success": False, "error": "Already checked out today."}, status=400)

        record.check_out = now
        record.save()

        notify_ai({
            "event": "check_out",
            "employee_id": employee.id,
            "attendance_id": record.id,
            "timestamp": record.check_out.isoformat() if record.check_out else None,
            "date": str(record.date),
            "total_hours": float(record.total_hours),
            "company_id": company.id if company else None,
        })

        return Response({
            "success": True,
            "action": "check_out",
            "attendance_id": record.id,
            "check_out": record.check_out,
            "total_hours": record.total_hours,
            "date": record.date,
        })