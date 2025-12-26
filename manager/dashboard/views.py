from datetime import timedelta, date
from calendar import monthrange

from django.utils import timezone
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from hr.employees.models import Employee, EmployeeStatus
from hr.attendance.models import AttendanceRecord, AttendanceStatus
from hr.contracts.models import EmployeeContract, ContractStatus
from hr.ess.models import (
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    OvertimeRequest,
    ExpenseRequest,
    HRFormRequest,
    ApprovalStatus,
)
from hr.payroll.models import PayrollRun, PayrollRunStatus
from accounts.permissions import IsAdminOrHR, IsAdminOrManager
from hr.org_structure.models import (
    Company,
    Department,
    CompanyNews,
    CompanyNotification,
)

from .serializers import (
    DashboardSummarySerializer,
    HRDashboardSummarySerializer,
)

# =========================================================
# ✅ Helpers (لازم يكونوا فوق UnifiedDashboardView)
# =========================================================

def get_annual_leave_entitlement(employee, company, default=24):
    return int(default)

def calculate_used_annual_leave(employee, year: int):
    if not employee:
        return 0.0

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    qs = LeaveRequest.objects.filter(
        employee=employee,
        leave_type=LeaveType.ANNUAL,
        status=LeaveStatus.APPROVED,
        start_date__lte=year_end,
        end_date__gte=year_start,
    )

    used = 0.0
    for lr in qs:
        s = max(lr.start_date, year_start)
        e = min(lr.end_date, year_end)
        days = (e - s).days + 1
        used += 0.5 if lr.is_half_day else float(days)

    return used

def get_role(user):
    if user.is_superuser or user.is_staff:
        return "admin"
    role = getattr(user, "role", None)
    if role in ["hr", "manager", "employee"]:
        return role
    return "employee"

def get_company_from_user_or_query(request):
    emp = getattr(request.user, "employee_profile", None)
    if emp and emp.company_id:
        return emp.company
    company_id = request.query_params.get("company_id")
    if company_id:
        return Company.objects.filter(pk=company_id).first()
    return Company.objects.first()

def build_header(request, role):
    name = (request.user.get_full_name() or request.user.get_username()).strip()
    initials = "".join([p[0].upper() for p in name.split()[:2]]) or "U"
    today_str = timezone.now().strftime("%A, %B %d, %Y")
    return {
        "role": role,
        "user": {"name": name, "initials": initials},
        "today": today_str
    }

ATTENDANCE_LABELS = {
    AttendanceStatus.PRESENT: "Present",
    AttendanceStatus.ABSENT: "Absent",
    AttendanceStatus.LATE: "Late",
    AttendanceStatus.ON_LEAVE: "On Leave",
    AttendanceStatus.HOLIDAY: "Holiday",
    AttendanceStatus.REMOTE: "Remote",
}

# =========================================================
# ✅ Notifications (DB) + Dynamic Alerts per Role
# =========================================================

def get_custom_notifications(company, role):
    """
    Notifications انتِ بتضيفيها من Django Admin (CompanyNotification)
    بتطلع حسب company + role + الوقت + is_active
    """
    if not company:
        return []

    now = timezone.now()

    qs = CompanyNotification.objects.filter(
        company=company,
        is_active=True,
        starts_at__lte=now,
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    ).filter(
        Q(role="all") | Q(role=role)
    ).order_by("-created_at")[:10]

    return [
        {
            "id": f"custom_{n.id}",
            "priority": n.priority,
            "message": n.message,
            "route": n.route or "",
        }
        for n in qs
    ]


def build_dynamic_alerts(role, company, *, employee=None, team_qs=None):
    """
    يجمع:
    1) Custom DB Notifications
    2) System Alerts حسب الداتا (Leave/Attendance/Contracts...)
    """
    alerts = []
    today = timezone.localdate()

    # 1) Custom notifications من DB
    alerts.extend(get_custom_notifications(company, role))

    # 2) System alerts حسب الدور

    # ---- ADMIN ----
    if role == "admin":
        # مثال ديناميكي: عقود منتهية خلال 14 يوم (لو عندك شركات متعددة)
        expiring = EmployeeContract.objects.filter(
            status=ContractStatus.ACTIVE,
            end_date__gte=today,
            end_date__lte=today + timedelta(days=14),
        ).count()
        if expiring:
            alerts.append({
                "id": "contracts_expiring",
                "priority": "high",
                "message": f"{expiring} contracts expiring within 14 days",
                "route": "/contracts",
            })
        return alerts

    if not company:
        return alerts

    # ---- HR ----
    if role == "hr":
        pending_leaves = LeaveRequest.objects.filter(
            employee__company=company,
            status=LeaveStatus.PENDING
        ).count()
        if pending_leaves:
            alerts.append({
                "id": "leave_pending",
                "priority": "high",
                "message": f"{pending_leaves} pending leave approvals require action",
                "route": "/leaves/approvals",
            })

        employees_with_active_contract = EmployeeContract.objects.filter(
            employee__company=company,
            status=ContractStatus.ACTIVE
        ).values_list("employee_id", flat=True)

        without_active_contracts = Employee.objects.filter(company=company).exclude(
            id__in=employees_with_active_contract
        ).count()

        if without_active_contracts:
            alerts.append({
                "id": "no_contracts",
                "priority": "high",
                "message": f"{without_active_contracts} employees without active contracts",
                "route": "/contracts",
            })

        since = today - timedelta(days=7)
        anomalies = AttendanceRecord.objects.filter(
            employee__company=company,
            date__gte=since,
            date__lte=today,
        ).filter(
            Q(status=AttendanceStatus.ABSENT) |
            Q(late_minutes__gt=0) |
            Q(early_leave_minutes__gt=0) |
            Q(is_overtime=True)
        ).count()

        if anomalies:
            alerts.append({
                "id": "attendance_anomalies",
                "priority": "medium",
                "message": f"{anomalies} attendance anomalies detected this week",
                "route": "/attendance/anomalies",
            })

        return alerts

    # ---- MANAGER ----
    if role == "manager" and team_qs is not None:
        pending_approvals = LeaveRequest.objects.filter(
            employee__in=team_qs,
            status=LeaveStatus.PENDING
        ).count()

        if pending_approvals:
            alerts.append({
                "id": "pending_approvals",
                "priority": "high",
                "message": f"{pending_approvals} pending approvals require your review",
                "route": "/manager/approvals",
            })

        absent_today = AttendanceRecord.objects.filter(
            employee__in=team_qs,
            date=today,
            status=AttendanceStatus.ABSENT
        ).count()

        if absent_today:
            alerts.append({
                "id": "absent_today",
                "priority": "medium",
                "message": f"{absent_today} team members absent today",
                "route": "/manager/attendance",
            })

        late_records = AttendanceRecord.objects.filter(
            employee__in=team_qs,
            date=today,
        ).filter(
            Q(status=AttendanceStatus.LATE) | Q(late_minutes__gt=0)
        ).select_related("employee__user").order_by("-late_minutes")

        for rec in late_records[:3]:
            name = rec.employee.user.get_full_name() or rec.employee.user.username
            time_str = rec.check_in.astimezone().strftime("%I:%M %p") if rec.check_in else "—"
            alerts.append({
                "id": f"late_{rec.employee.id}",
                "priority": "low",
                "message": f"Late arrival: {name} ({time_str})",
                "route": "/manager/attendance",
            })

        return alerts

    # ---- EMPLOYEE ----
    if role == "employee" and employee is not None:
        rec = AttendanceRecord.objects.filter(employee=employee, date=today).first()
        if rec and rec.late_minutes > 0:
            alerts.append({
                "id": "late_self",
                "priority": "low",
                "message": f"You were late today by {rec.late_minutes} minutes",
                "route": "/me/attendance",
            })

        pending_my = LeaveRequest.objects.filter(
            employee=employee,
            status=LeaveStatus.PENDING
        ).count()

        if pending_my:
            alerts.append({
                "id": "my_leave_pending",
                "priority": "medium",
                "message": f"You have {pending_my} leave request(s) pending approval",
                "route": "/me/leaves",
            })

        return alerts

    return alerts


# =========================================================
# Existing Views (كما هي عندك)
# =========================================================

class HRBaseCompanyMixin:
    def get_company(self, request):
        emp_profile = getattr(request.user, "employee_profile", None)
        if emp_profile is not None and emp_profile.company_id:
            return emp_profile.company

        company_id = request.query_params.get("company_id")
        if company_id:
            return Company.objects.filter(pk=company_id).first()

        return Company.objects.first()


class DashboardSummaryView(HRBaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        company = self.get_company(request)

        if not company:
            payload = {
                "total_employees": 0,
                "active_contracts": 0,
                "pending_leaves": 0,
                "payroll_due": 0,
                "departments_count": 0,
                "recent_activity": [],
                "news": [],
            }
            serializer = DashboardSummarySerializer(payload)
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

        last_unpaid_run = PayrollRun.objects.filter(
            company=company,
            status__in=[PayrollRunStatus.DRAFT, PayrollRunStatus.APPROVED],
        ).order_by("-year", "-month").first()
        payroll_due = last_unpaid_run.total_net if last_unpaid_run else 0

        departments_count = Department.objects.filter(company=company).count()

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
            days_left = (expiring_contract.end_date - today).days
            recent_activity.append(
                f"Contract for {expiring_contract.employee.user.get_full_name() or expiring_contract.employee.user.username} expires in {days_left} days"
            )

        last_approved_leave = LeaveRequest.objects.filter(
            employee__company=company,
            status=LeaveStatus.APPROVED,
        ).order_by("-approved_at").first()
        if last_approved_leave:
            recent_activity.append(
                f"Approved time-off request for {last_approved_leave.employee.user.get_full_name() or last_approved_leave.employee.user.username}"
            )

        news_qs = CompanyNews.objects.filter(
            company=company
        ).order_by("-is_pinned", "-date")[:3]

        payload = {
            "total_employees": total_employees,
            "active_contracts": active_contracts,
            "pending_leaves": pending_leaves,
            "payroll_due": payroll_due,
            "departments_count": departments_count,
            "recent_activity": recent_activity,
            "news": news_qs,
        }

        serializer = DashboardSummarySerializer(payload)
        return Response(serializer.data)


class MyTeamDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]

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

        team_qs = Employee.objects.select_related("user", "job_title").filter(
            manager=manager_emp,
            status=EmployeeStatus.ACTIVE,
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
                attendance_pct = round((emp_present_days / total_days) * 100, 1)
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
            day_present = day_records.filter(status__in=present_statuses).count()
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


class HRMainDashboardView(HRBaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def _get_last_month_range(self, today):
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
        last_month_end = timezone.datetime(
            last_year, last_month, last_month_end_day
        ).date()
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

        runs_this_month = PayrollRun.objects.filter(
            company=company,
            year=today.year,
            month=today.month,
            status__in=[PayrollRunStatus.POSTED, PayrollRunStatus.PAID],
        )

        payroll_sum = runs_this_month.aggregate(total=Sum("total_net"))["total"] or 0
        payroll_period_label = today.strftime("%b %Y")

        data = {
            "total_employees": total_employees,
            "employees_change_percent": float(employees_change_percent),
            "open_positions": open_positions,
            "open_positions_urgent": open_positions_urgent,
            "pending_leave_requests": pending_leave_requests,
            "pending_leaves_require_approval": pending_leave_requests,
            "payroll_processed": payroll_sum,
            "payroll_currency": "USD",
            "payroll_period_label": payroll_period_label,
        }

        serializer = HRDashboardSummarySerializer(data)
        return Response(serializer.data)


# =========================================================
# ✅ UnifiedDashboardView (FINAL - alerts dynamic for all roles)
# =========================================================

class UnifiedDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requested_role = (request.query_params.get("role") or "").lower().strip()
        requested_role = requested_role.replace("/", "")

        role = get_role(request.user)
        if requested_role in ["admin", "hr", "manager", "employee"]:
            role = requested_role

        company = get_company_from_user_or_query(request)
        today = timezone.localdate()

        # ===== ADMIN =====
        if role == "admin":
            User = get_user_model()
            total_users = User.objects.count()
            companies = Company.objects.count()

            active_roles = 0
            if hasattr(User, "role"):
                active_roles = User.objects.values("role").distinct().count()

            active_modules = 12

            payload = {
                **build_header(request, role),
                "kpis": [
                    {"key": "total_users", "label": "Total Users", "value": total_users, "icon": "users"},
                    {"key": "active_roles", "label": "Active Roles", "value": active_roles, "icon": "key"},
                    {"key": "companies", "label": "Companies", "value": companies, "icon": "building"},
                    {"key": "active_modules", "label": "Active Modules", "value": active_modules, "icon": "gear"},
                ],
                "quick_actions": [
                    {"key":"user_management","label":"User Management","subtitle":"Manage system users","route":"/admin/users"},
                    {"key":"roles_permissions","label":"Roles & Permissions","subtitle":"Configure access control","route":"/admin/roles"},
                    {"key":"system_settings","label":"System Settings","subtitle":"Configure system","route":"/admin/settings"},
                ],
                # ✅ dynamic alerts (DB + system)
                "alerts": build_dynamic_alerts("admin", company),
            }
            return Response(payload)

        # باقي الأدوار بدهن شركة
        if not company:
            return Response({**build_header(request, role), "kpis": [], "quick_actions": [], "alerts": []})

        emp_qs = Employee.objects.filter(company=company)

        # ===== HR =====
        if role == "hr":
            total_employees = emp_qs.count()
            active_employees = emp_qs.filter(status=EmployeeStatus.ACTIVE).count()
            terminated = emp_qs.filter(status=EmployeeStatus.TERMINATED).count()

            on_leave = LeaveRequest.objects.filter(
                employee__company=company,
                status=LeaveStatus.APPROVED,
                start_date__lte=today,
                end_date__gte=today,
            ).count()

            month_start = today.replace(day=1)
            new_hires = emp_qs.filter(hire_date__gte=month_start, hire_date__lte=today).count()

            payload = {
                **build_header(request, role),
                "kpis": [
                    {"key":"total_employees","label":"Total Employees","value":total_employees,"icon":"users"},
                    {"key":"active_employees","label":"Active Employees","value":active_employees,"icon":"check"},
                    {"key":"on_leave","label":"On Leave","value":on_leave,"icon":"beach"},
                    {"key":"terminated","label":"Terminated","value":terminated,"icon":"x"},
                    {"key":"new_hires_month","label":"New Hires (This Month)","value":new_hires,"icon":"party"},
                ],
                "quick_actions": [
                    {"key":"people_hub","label":"People Hub","subtitle":"Manage employee records","route":"/people-hub"},
                    {"key":"attendance_overview","label":"Attendance Overview","subtitle":"View attendance reports","route":"/attendance"},
                    {"key":"payroll","label":"Payroll","subtitle":"Process monthly payroll","route":"/payroll"},
                    {"key":"contracts","label":"Contracts","subtitle":"Manage employee contracts","route":"/contracts"},
                ],
                # ✅ dynamic alerts (DB + system)
                "alerts": build_dynamic_alerts("hr", company),
            }
            return Response(payload)

        # ===== MANAGER =====
        if role == "manager":
            manager_emp = getattr(request.user, "employee_profile", None)
            team_qs = Employee.objects.filter(
                company=company,
                manager=manager_emp,
                status=EmployeeStatus.ACTIVE
            )

            team_size = team_qs.count()

            today_records = AttendanceRecord.objects.filter(employee__in=team_qs, date=today)

            present_today = today_records.filter(
                status__in=[AttendanceStatus.PRESENT, AttendanceStatus.REMOTE, AttendanceStatus.LATE]
            ).count()

            late_today = today_records.filter(
                Q(status=AttendanceStatus.LATE) | Q(late_minutes__gt=0)
            ).count()

            on_leave = LeaveRequest.objects.filter(
                employee__in=team_qs,
                status=LeaveStatus.APPROVED,
                start_date__lte=today,
                end_date__gte=today,
            ).count()

            payload = {
                **build_header(request, role),
                "kpis": [
                    {"key":"team_size","label":"Team Size","value":team_size,"icon":"users"},
                    {"key":"present_today","label":"Present Today","value":present_today,"icon":"check"},
                    {"key":"on_leave","label":"On Leave","value":on_leave,"icon":"beach"},
                    {"key":"late_today","label":"Late Today","value":late_today,"icon":"timer"},
                ],
                "quick_actions": [
                    {"key":"my_team","label":"My Team","subtitle":"View team members","route":"/manager/team"},
                    {"key":"approve_requests","label":"Approve Requests","subtitle":"Pending approvals","route":"/manager/approvals"},
                    {"key":"team_attendance","label":"Team Attendance","subtitle":"Track team presence","route":"/manager/attendance"},
                ],
                # ✅ dynamic alerts (DB + system) + team_qs
                "alerts": build_dynamic_alerts("manager", company, team_qs=team_qs),
            }
            return Response(payload)

        # ===== EMPLOYEE (default) =====
        emp = getattr(request.user, "employee_profile", None)

        status_value = "Absent"
        sub = "No attendance record"

        if emp:
            rec = AttendanceRecord.objects.filter(employee=emp, date=today).first()
            if rec:
                status_value = ATTENDANCE_LABELS.get(rec.status, rec.status)
                if rec.check_in:
                    sub = f"Checked in at {rec.check_in.astimezone().strftime('%I:%M %p')}"
                else:
                    sub = "Attendance recorded"

        month_start = today.replace(day=1)
        overtime_sum = AttendanceRecord.objects.filter(
            employee=emp,
            date__gte=month_start,
            date__lte=today,
        ).aggregate(total=Sum("overtime_hours"))["total"] or 0

        entitlement = get_annual_leave_entitlement(emp, company, default=24)
        used_days = calculate_used_annual_leave(emp, today.year)
        remaining = max(0.0, float(entitlement) - float(used_days))

        payload = {
            **build_header(request, "employee"),
            "kpis": [
                {"key":"today_status","label":"Today's Status","value":status_value,"subvalue":sub,"icon":"check"},
                {"key":"leave_balance","label":"Leave Balance","value":f"{remaining:g} days","subvalue":"Annual leave remaining","icon":"beach"},
                {"key":"overtime","label":"Overtime Hours","value":f"{float(overtime_sum):g} hrs","subvalue":"This month","icon":"timer"},
            ],
            "quick_actions": [
                {"key":"my_profile","label":"My Profile","subtitle":"View personal details","route":"/me/profile"},
                {"key":"attendance","label":"Attendance","subtitle":"View my attendance","route":"/me/attendance"},
                {"key":"request_leave","label":"Request Leave","subtitle":"Submit leave request","route":"/me/leaves/request"},
            ],
            # ✅ dynamic alerts (DB + system) + employee
            "alerts": build_dynamic_alerts("employee", company, employee=emp),
        }
        return Response(payload)