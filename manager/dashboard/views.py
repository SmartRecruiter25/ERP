from datetime import timedelta
from django.db.models import Sum
from django.db.models import Avg
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from manager.dashboard.serializers import (
    DashboardSummarySerializer ,
    HRDashboardSummarySerializer ,
)
from hr.employees.models import Employee, EmployeeStatus
from hr.attendance.models import AttendanceRecord, AttendanceStatus
from hr.contracts.models import EmployeeContract, ContractStatus
from hr.ess.models import (
    LeaveRequest,
    LeaveStatus,
    OvertimeRequest,
    ExpenseRequest,
    HRFormRequest,
    ApprovalStatus,
)
from hr.payroll.models import PayrollRun, PayrollRunStatus
from hr.org_structure.models import Company, Department, CompanyNews
from hr.ai.models import ContractAlert  

class DashboardSummaryView(APIView):

    permission_classes = [IsAuthenticated]

    def get_company(self, request):
  
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None and employee_profile.company_id:
            return employee_profile.company

        company_id = request.query_params.get("company_id")
        if company_id:
            return Company.objects.filter(pk=company_id).first()

        return Company.objects.first()

    def get(self, request, *args, **kwargs):
        company = self.get_company(request)
        today = timezone.now().date()

        if not company:
            data = {
                "total_employees": 0,
                "active_contracts": 0,
                "pending_leaves": 0,
                "payroll_due": 0,
                "departments_count": 0,
                "news": [],
                "recent_activity": [],
            }
            serializer = DashboardSummarySerializer(data)
            return Response(serializer.data)

        
        total_employees = Employee.objects.filter(company=company).count()

       
        active_contracts = EmployeeContract.objects.filter(
            employee__company=company,
            status=ContractStatus.ACTIVE,
        ).count()

        
        pending_leaves = LeaveRequest.objects.filter(
            employee__company=company,
            status=LeaveStatus.PENDING,
        ).count()

       
        payroll_run = PayrollRun.objects.filter(
            company=company,
            status__in=[PayrollRunStatus.DRAFT, PayrollRunStatus.APPROVED],
        ).order_by("-year", "-month").first()

        payroll_due = payroll_run.total_net if payroll_run else 0

        
        departments_count = Department.objects.filter(company=company).count()

        
        news_qs = CompanyNews.objects.filter(company=company).order_by(
            "-is_pinned", "-date"
        )[:3]

        
        recent_activity = []

       
        last_leave = LeaveRequest.objects.filter(
            employee__company=company
        ).order_by("-created_at").first()
        if last_leave:
            recent_activity.append(
                f"New leave request from {last_leave.employee.user.get_full_name() or last_leave.employee.user.username}"
            )

        
        last_payroll_done = PayrollRun.objects.filter(
            company=company,
            status__in=[PayrollRunStatus.POSTED, PayrollRunStatus.PAID],
        ).order_by("-year", "-month").first()
        if last_payroll_done:
            recent_activity.append(
                f"Payroll for {last_payroll_done.month}/{last_payroll_done.year} completed"
            )

        expiring_contract = EmployeeContract.objects.filter(
            employee__company=company,
            status=ContractStatus.ACTIVE,
            end_date__gte=today,
        ).order_by("end_date").first()
        if expiring_contract:
            days = (expiring_contract.end_date - today).days
            recent_activity.append(
                f"Contract for {expiring_contract.employee.user.get_full_name() or expiring_contract.employee.user.username} expires in {days} days"
            )

        last_approved_leave = LeaveRequest.objects.filter(
            employee__company=company,
            status=LeaveStatus.APPROVED,
        ).order_by("-approved_at").first()
        if last_approved_leave:
            recent_activity.append(
                f"Approved time-off request for {last_approved_leave.employee.user.get_full_name() or last_approved_leave.employee.user.username}"
            )

        data = {
            "total_employees": total_employees,
            "active_contracts": active_contracts,
            "pending_leaves": pending_leaves,
            "payroll_due": payroll_due,
            "departments_count": departments_count,
            "news": news_qs,
            "recent_activity": recent_activity,
        }

        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)


class MyTeamDashboardView(APIView):
 
    permission_classes = [IsAuthenticated]

    def get_manager_employee(self, request):
        return getattr(request.user, "employee_profile", None)

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        manager_emp = self.get_manager_employee(request)

        if manager_emp is None:
            empty = {
                "cards": {
                    "team_members": 0,
                    "pending_approvals": 0,
                    "tasks_awaiting_approval": 0,
                    "avg_performance_score": 0,
                    "todays_attendance": 0,
                },
                "team_overview": [],
                "performance_trend": [],
                "approvals": [],
            }
            return Response(empty)

        team_qs = (
            Employee.objects.select_related("user", "job_title")
            .filter(manager=manager_emp, status=EmployeeStatus.ACTIVE)
        )
        team_count = team_qs.count()
        present_statuses = [
            AttendanceStatus.PRESENT,
            AttendanceStatus.LATE,
            AttendanceStatus.REMOTE,
        ]

        pending_leaves_count = LeaveRequest.objects.filter(
            employee__in=team_qs, status=LeaveStatus.PENDING
        ).count()
        pending_overtime_count = OvertimeRequest.objects.filter(
            employee__in=team_qs, status=ApprovalStatus.PENDING
        ).count()
        pending_expense_count = ExpenseRequest.objects.filter(
            employee__in=team_qs, status=ApprovalStatus.PENDING
        ).count()
        pending_hrforms_count = HRFormRequest.objects.filter(
            employee__in=team_qs, status=ApprovalStatus.PENDING
        ).count()

        pending_approvals_total = (
            pending_leaves_count
            + pending_overtime_count
            + pending_expense_count
            + pending_hrforms_count
        )

        tasks_awaiting_approval = pending_approvals_total

        today_records = AttendanceRecord.objects.filter(
            employee__in=team_qs, date=today
        )
        present_count = today_records.filter(status__in=present_statuses).count()
        todays_attendance = (
            round((present_count / team_count) * 100, 1) if team_count > 0 else 0
        )

        last_30 = today - timedelta(days=30)
        team_overview = []
        attendance_sum_for_avg = 0

        for emp in team_qs:
            name = emp.user.get_full_name() or emp.user.username
            role = emp.job_title.title_name if emp.job_title else emp.user.role

            emp_records = AttendanceRecord.objects.filter(
                employee=emp, date__gte=last_30, date__lte=today
            )
            total_days = emp_records.count()
            emp_present_days = emp_records.filter(
                status__in=present_statuses
            ).count()

            if total_days > 0:
                attendance_pct = round(
                    (emp_present_days / total_days) * 100, 1
                )
            else:
                attendance_pct = 0

            attendance_sum_for_avg += attendance_pct

            team_overview.append(
                {
                    "id": emp.id,
                    "name": name,
                    "role": role,
                    "attendance": attendance_pct, 
                    "performance": attendance_pct,  
                    "status": emp.status,
                }
            )

        avg_performance_score = (
            round(attendance_sum_for_avg / team_count, 1) if team_count > 0 else 0
        )

        performance_trend = []
        for i in range(6, -1, -1):  
            day = today - timedelta(days=i)
            day_records = AttendanceRecord.objects.filter(
                employee__in=team_qs, date=day
            )
            day_present = day_records.filter(
                status__in=present_statuses
            ).count()
            day_attendance = (
                round((day_present / team_count) * 100, 1) if team_count > 0 else 0
            )

            performance_trend.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%a"), 
                    "attendance": day_attendance,
                }
            )

        type_filter = (request.query_params.get("type") or "all").lower()
        status_filter = (request.query_params.get("status") or "pending").lower()
        days_param = request.query_params.get("days") or "7"

        try:
            days = int(days_param)
        except ValueError:
            days = 7

        since_date = today - timedelta(days=days)

        approvals = []

        def apply_status_filter(qs, status_field="status"):
            if status_filter == "all":
                return qs
            return qs.filter(**{status_field: status_filter})

        if type_filter in ("all", "leave"):
            leave_qs = LeaveRequest.objects.filter(
                employee__in=team_qs,
                created_at__date__gte=since_date,
            )
            leave_qs = apply_status_filter(leave_qs, "status")
            for obj in leave_qs.select_related("employee__user"):
                approvals.append(
                    {
                        "id": obj.id,
                        "type": "leave",
                        "employee": obj.employee.user.get_full_name()
                        or obj.employee.user.username,
                        "submitted_on": obj.created_at.date().isoformat(),
                        "status": obj.status,
                        "amount": None,
                        "hours": None,
                        "extra": obj.leave_type,
                    }
                )

        if type_filter in ("all", "overtime"):
            ot_qs = OvertimeRequest.objects.filter(
                employee__in=team_qs,
                submitted_at__date__gte=since_date,
            )
            ot_qs = apply_status_filter(ot_qs, "status")
            for obj in ot_qs.select_related("employee__user"):
                approvals.append(
                    {
                        "id": obj.id,
                        "type": "overtime",
                        "employee": obj.employee.user.get_full_name()
                        or obj.employee.user.username,
                        "submitted_on": obj.submitted_at.date().isoformat(),
                        "status": obj.status,
                        "amount": None,
                        "hours": float(obj.hours),
                        "extra": obj.reason,
                    }
                )

        if type_filter in ("all", "expense"):
            exp_qs = ExpenseRequest.objects.filter(
                employee__in=team_qs,
                submitted_at__date__gte=since_date,
            )
            exp_qs = apply_status_filter(exp_qs, "status")
            for obj in exp_qs.select_related("employee__user"):
                approvals.append(
                    {
                        "id": obj.id,
                        "type": "expense",
                        "employee": obj.employee.user.get_full_name()
                        or obj.employee.user.username,
                        "submitted_on": obj.submitted_at.date().isoformat(),
                        "status": obj.status,
                        "amount": float(obj.amount),
                        "hours": None,
                        "extra": obj.category,
                    }
                )

        if type_filter in ("all", "hr_form", "hrforms"):
            form_qs = HRFormRequest.objects.filter(
                employee__in=team_qs,
                submitted_at__date__gte=since_date,
            )
            form_qs = apply_status_filter(form_qs, "status")
            for obj in form_qs.select_related("employee__user"):
                approvals.append(
                    {
                        "id": obj.id,
                        "type": "hr_form",
                        "employee": obj.employee.user.get_full_name()
                        or obj.employee.user.username,
                        "submitted_on": obj.submitted_at.date().isoformat(),
                        "status": obj.status,
                        "amount": None,
                        "hours": None,
                        "extra": obj.form_type,
                    }
                )

        approvals.sort(key=lambda x: x["submitted_on"], reverse=True)

        data = {
            "cards": {
                "team_members": team_count,
                "pending_approvals": pending_approvals_total,
                "tasks_awaiting_approval": tasks_awaiting_approval,
                "avg_performance_score": avg_performance_score,
                "todays_attendance": todays_attendance,
            },
            "team_overview": team_overview,
            "performance_trend": performance_trend,
            "approvals": approvals,
        }

        return Response(data)

class HRMainDashboardView(APIView):

    permission_classes = [IsAuthenticated]

    def get_company(self, request):
   
        emp = getattr(request.user, "employee_profile", None)
        if emp and emp.company:
            return emp.company

        company_id = request.query_params.get("company_id")
        if company_id:
            return Company.objects.filter(pk=company_id).first()

        return Company.objects.first()

    def _get_last_month_range(self, today):
  
        from calendar import monthrange

        year = today.year
        month = today.month

        if month == 1:
            last_year = year - 1
            last_month = 12
        else:
            last_year = year
            last_month = month - 1

        last_month_start = timezone.datetime(last_year, last_month, 1).date()
        last_month_end_day = monthrange(last_year, last_month)[1]
        last_month_end = timezone.datetime(last_year, last_month, last_month_end_day).date()

        return last_month_start, last_month_end

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        company = self.get_company(request)

        if not company:
            data = {
                "total_employees": 0,
                "employees_change_percent": 0.0,
                "open_positions": 0,
                "open_positions_urgent": 0,
                "pending_leave_requests": 0,
                "pending_leaves_require_approval": 0,
                "payroll_processed": 0,
                "payroll_currency": "USD",
                "payroll_period_label": "",
            }
            serializer = HRDashboardSummarySerializer(data)
            return Response(serializer.data)

        total_employees = Employee.objects.filter(
            company=company,
            status=EmployeeStatus.ACTIVE,
        ).count()

        last_month_start, last_month_end = self._get_last_month_range(today)
        employees_last_month = Employee.objects.filter(
            company=company,
            status=EmployeeStatus.ACTIVE,
            hire_date__lte=last_month_end,
        ).count()

        if employees_last_month > 0:
            employees_change_percent = round(
                ((total_employees - employees_last_month) / employees_last_month) * 100.0,
                1,
            )
        else:
            employees_change_percent = 100.0 if total_employees > 0 else 0.0

        try:
            from hr.job_requirements.models import JobRequirement

            open_positions_qs = JobRequirement.objects.filter(company=company)

            open_positions = open_positions_qs.count()

            if hasattr(JobRequirement, "is_urgent"):
                open_positions_urgent = open_positions_qs.filter(is_urgent=True).count()
            else:
                open_positions_urgent = 0

        except Exception:
            open_positions = 0
            open_positions_urgent = 0

        pending_leave_requests = LeaveRequest.objects.filter(
            employee__company=company,
            status=LeaveStatus.PENDING,
        ).count()

        pending_leaves_require_approval = pending_leave_requests

        runs_this_month = PayrollRun.objects.filter(
            company=company,
            year=today.year,
            month=today.month,
            status__in=[PayrollRunStatus.POSTED, PayrollRunStatus.PAID],
        )

        payroll_sum = runs_this_month.aggregate(total=Sum("total_net"))["total"] or 0

        sample_run = runs_this_month.first()
        payroll_currency = "USD"
        if sample_run and hasattr(sample_run, "currency"):
            payroll_currency = sample_run.currency

        payroll_period_label = today.strftime("%b %Y") 

        data = {
            "total_employees": total_employees,
            "employees_change_percent": float(employees_change_percent),

            "open_positions": open_positions,
            "open_positions_urgent": open_positions_urgent,

            "pending_leave_requests": pending_leave_requests,
            "pending_leaves_require_approval": pending_leaves_require_approval,

            "payroll_processed": payroll_sum,
            "payroll_currency": payroll_currency,
            "payroll_period_label": payroll_period_label,
        }

        serializer = HRDashboardSummarySerializer(data)
        return Response(serializer.data)