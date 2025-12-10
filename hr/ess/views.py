from datetime import date

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import models

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions , generics
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsEmployee
from hr.employees.models import Employee , EmployeeDocument
from hr.contracts.models import EmployeeContract
from .serializers import (
    LeaveRequestSerializer , 
    EmployeeDocumentSerializer , 
    ESSPayslipSerializer,
    AnnouncementSerializer ,
)
from hr.ess.models import LeaveRequest
from datetime import datetime, timedelta
from .models import Announcement
from hr.attendance.models import AttendanceRecord   
from hr.payroll.models import PayrollItem , Payslip        

User = get_user_model()

def get_employee_for_user(user):
    return get_object_or_404(Employee, user=user)


class ESSDashboardSummaryView(APIView):


    permission_classes = [permissions.IsAuthenticated , IsEmployee]


    def get_employee(self, user):
       
        return get_object_or_404(Employee, user=user)

    def get_attendance_summary(self, employee):
       
        today = timezone.now().date()
        current_year = today.year
        current_month = today.month

        current_qs = AttendanceRecord.objects.filter(
            employee=employee,
            date__year=current_year,
            date__month=current_month,
        )


        current_present = current_qs.filter(status__iexact="present").count()
        current_total = current_qs.count()
        current_percent = (
            round((current_present / current_total) * 100, 1) if current_total > 0 else 0
        )

       
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year

        prev_qs = AttendanceRecord.objects.filter(
            employee=employee,
            date__year=prev_year,
            date__month=prev_month,
        )
        prev_present = prev_qs.filter(status__iexact="present").count()
        prev_total = prev_qs.count()
        prev_percent = (
            round((prev_present / prev_total) * 100, 1) if prev_total > 0 else 0
        )

        change = current_percent - prev_percent  

        return {
            "percentage": current_percent,
            "change": change,
        }

    def get_leave_summary(self, employee):
       
        today = timezone.now().date()
        ANNUAL_LEAVE_DAYS = 30  

        approved_leaves = LeaveRequest.objects.filter(
            employee=employee,
            status__iexact="approved",
            start_date__year=today.year,
        )

        def calc_days(req):
            if req.start_date and req.end_date:
                return (req.end_date - req.start_date).days + 1
            return 0

        days_taken = sum(calc_days(req) for req in approved_leaves)
        remaining = max(ANNUAL_LEAVE_DAYS - days_taken, 0)

        return {
            "remaining_days": remaining,
            "total_days": ANNUAL_LEAVE_DAYS,
        }

    def get_payslip_summary(self, employee):
        
        payslip = (
            PayrollItem.objects.filter(employee=employee)
            .select_related("payroll_run")
            .order_by("-payroll_run__period_end")
            .first()
        )

        if not payslip or not payslip.payroll_run:
            return {
                "period_label": None,
                "status": None,
                "net_salary": None,
            }

        payroll_run = payslip.payroll_run

    
        if isinstance(payroll_run.period_end, (date,)):
            period_label = payroll_run.period_end.strftime("%b %Y")
        else:
            period_label = None

        return {
            "period_label": period_label,
            "status": getattr(payroll_run, "status", None),
            "net_salary": payslip.net_salary,
        }

    def get_contract_summary(self, employee):
       
        today = timezone.now().date()

        contract = (
            EmployeeContract.objects.filter(employee=employee)
            .order_by("-start_date")
            .first()
        )

        if not contract:
            return {
                "status": "No Contract",
                "type": None,
                "start_date": None,
                "end_date": None,
            }

        if contract.end_date and contract.end_date < today:
            status = "Expired"
        else:
            status = "Active"

        contract_type = getattr(contract, "contract_type", None) or getattr(
            contract, "job_type", None
        )

        return {
            "status": status,
            "type": contract_type or "Full-time",  
            "start_date": contract.start_date,
            "end_date": contract.end_date,
        }


    def get(self, request):
        user = request.user
        employee = self.get_employee(user)

        attendance = self.get_attendance_summary(employee)
        leave = self.get_leave_summary(employee)
        payslip = self.get_payslip_summary(employee)
        contract = self.get_contract_summary(employee)

        data = {
            "attendance": {
                "current_month_percentage": attendance["percentage"],
                "change_from_last_month": attendance["change"],
            },
            "leave": {
                "remaining_days": leave["remaining_days"],
                "total_days": leave["total_days"],
            },
            "payslip": {
                "latest_period": payslip["period_label"],
                "status": payslip["status"],
                "net_salary": payslip["net_salary"],
            },
            "contract": {
                "status": contract["status"],
                "type": contract["type"],
                "start_date": contract["start_date"],
                "end_date": contract["end_date"],
            },
        }

        return Response(data)

class ESSAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated , IsEmployee]

    def get_employee(self, user):
        return get_object_or_404(Employee, user=user)

    def get(self, request):
        user = request.user
        employee = self.get_employee(user)

        today = timezone.now().date()

        today_record = (
            AttendanceRecord.objects
            .filter(employee=employee, date=today)
            .order_by("-id")
            .first()
        )

        if today_record:
            today_status = today_record.status
            check_in = today_record.check_in.strftime("%H:%M") if today_record.check_in else None
            check_out = today_record.check_out.strftime("%H:%M") if today_record.check_out else None
        else:
            today_status = "Absent"
            check_in = None
            check_out = None

        last_7_days_qs = (
            AttendanceRecord.objects
            .filter(employee=employee)
            .order_by("-date")[:7]
        )

        recent_logs = [
            {
                "date": rec.date.strftime("%Y-%m-%d"),
                "check_in": rec.check_in.strftime("%H:%M") if rec.check_in else None,
                "check_out": rec.check_out.strftime("%H:%M") if rec.check_out else None,
                "status": rec.status,
            }
            for rec in last_7_days_qs
        ]

        data = {
            "today": {
                "status": today_status,
                "check_in": check_in,
                "check_out": check_out,
            },
            "recent_logs": recent_logs,
        }
        return Response(data)


class ESSLeaveRequestsView(APIView):
   
    permission_classes = [permissions.IsAuthenticated , IsEmployee]

    def get(self, request):
        employee = get_employee_for_user(request.user)

        qs = (
            LeaveRequest.objects
            .filter(employee=employee)
            .order_by("-created_at")
        )

        def serialize_by_status(status_value):
            items = qs.filter(status__iexact=status_value)
            return LeaveRequestSerializer(items, many=True).data

        data = {
            "pending": serialize_by_status("pending"),
            "approved": serialize_by_status("approved"),
            "rejected": serialize_by_status("rejected"),
        }

        return Response(data)


class ESSLeaveRequestCreateView(generics.CreateAPIView):
  
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated , IsEmployee]

    def perform_create(self, serializer):
        employee = get_employee_for_user(self.request.user)

        serializer.save(employee=employee, status="pending")

class ESSContractDocumentsView(APIView):

    permission_classes = [permissions.IsAuthenticated , IsEmployee]

    def get(self, request):
        employee = get_employee_for_user(request.user)
        today = timezone.now().date()

        contract = (
            EmployeeContract.objects
            .filter(employee=employee)
            .order_by("-start_date")
            .first()
        )

        if contract:
            if contract.end_date and contract.end_date < today:
                status = "Expired"
            else:
                status = "Active"

            contract_type = getattr(contract, "contract_type", None) or getattr(
                contract, "job_type", None
            ) or "Full-time Permanent"


            renewal_due_date = contract.end_date
            days_to_expiry = (
                (renewal_due_date - today).days
                if renewal_due_date
                else None
            )

            contract_data = {
                "status": status,                        
                "type": contract_type,                    
                "start_date": contract.start_date,        
                "end_date": contract.end_date,           
                "renewal_due_date": renewal_due_date,    
                "days_to_expiry": days_to_expiry,         
            }
        else:
            contract_data = {
                "status": "No Contract",
                "type": None,
                "start_date": None,
                "end_date": None,
                "renewal_due_date": None,
                "days_to_expiry": None,
            }

        docs_qs = (
            EmployeeDocument.objects
            .filter(employee=employee)
            .order_by("-uploaded_at")
        )

        documents_data = EmployeeDocumentSerializer(
            docs_qs, many=True, context={"request": request}
        ).data

        data = {
            "contract": contract_data,
            "documents": documents_data,
        }

        return Response(data)

class ESSDocumentListCreateView(generics.ListCreateAPIView):
   
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated , IsEmployee]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        employee = get_employee_for_user(self.request.user)
        return (
            EmployeeDocument.objects
            .filter(employee=employee)
            .order_by("-uploaded_at")
        )

    def perform_create(self, serializer):
        employee = get_employee_for_user(self.request.user)
        serializer.save(employee=employee)

class ESSPayslipListView(generics.ListAPIView):
 
    serializer_class = ESSPayslipSerializer
    permission_classes = [permissions.IsAuthenticated , IsEmployee]

    def get_employee(self):
        user = self.request.user

        employee = getattr(user, "employee_profile", None)
        if employee is not None:
            return employee
        return Employee.objects.filter(user=user).first()

    def get_queryset(self):
        employee = self.get_employee()
        if not employee:
            return Payslip.objects.none()

        qs = Payslip.objects.filter(
            employee=employee,
        ).order_by("-year", "-month")

        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

        if year:
            qs = qs.filter(year=year)
        if month:
            qs = qs.filter(month=month)

        return qs

class ESSAnnouncementsListView(generics.ListAPIView):
    
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated , IsEmployee]
    pagination_class = None  

    def get_queryset(self):
        user = self.request.user
        today = timezone.now().date()

        qs = Announcement.objects.filter(is_active=True)

 
        qs = qs.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=today),
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=today),
        )

        employee = None
        try:
            employee = Employee.objects.select_related("company").get(user=user)
        except Employee.DoesNotExist:
            pass

        if employee and employee.company:
            qs = qs.filter(
                models.Q(company__isnull=True) | models.Q(company=employee.company)
            )

        return qs.order_by("-is_pinned", "-created_at")[:5]