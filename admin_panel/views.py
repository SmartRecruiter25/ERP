from django.utils import timezone
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions , generics
from .serializers import (
    DepartmentSerializer,
    RoleSerializer,
    SystemSettingSerializer,
)

from hr.employees.models import Employee
from accounts.models import User
from hr.contracts.models import EmployeeContract
from hr.org_structure.models import Department
from hr.ess.models import LeaveRequest
from datetime import datetime
from .models import AuditLog , Role, SystemSetting

User = get_user_model()


class AdminDashboardSummaryView(APIView):
  
    permission_classes = [permissions.IsAuthenticated]  # ممكن تخليها IsAdminUser لو حبيتي

    def get(self, request):
        today = timezone.now().date()

        # ======== قراءة الفلاتر من الـ Query Params ========
        department = request.query_params.get("department")
        role = request.query_params.get("role")
        status = request.query_params.get("status")          # active / inactive
        date_from = request.query_params.get("date_from")    # YYYY-MM-DD
        date_to = request.query_params.get("date_to")        # YYYY-MM-DD

        # ======== QuerySets أساسية قبل الفلترة ========
        employees_qs = Employee.objects.select_related("department", "user").all()
        contracts_qs = EmployeeContract.objects.select_related(
            "employee", "employee__department", "employee__user"
        ).all()
        users_qs = User.objects.all()
        leave_qs = LeaveRequest.objects.select_related(
            "employee", "employee__department", "employee__user"
        ).all()

        # ======== تطبيق فلتر القسم ========
        if department:
            # هون اعتبرنا إنك عم تبعتي اسم القسم، إذا بدك ID غيريها لـ department_id=department
            employees_qs = employees_qs.filter(department__name__iexact=department)
            contracts_qs = contracts_qs.filter(employee__department__name__iexact=department)
            leave_qs = leave_qs.filter(employee__department__name__iexact=department)

        # ======== تطبيق فلتر الدور ========
        if role:
            users_qs = users_qs.filter(role__iexact=role)
            employees_qs = employees_qs.filter(user__role__iexact=role)
            contracts_qs = contracts_qs.filter(employee__user__role__iexact=role)
            leave_qs = leave_qs.filter(employee__user__role__iexact=role)

        # ======== تطبيق فلتر الحالة (Active / Inactive على مستوى الـ User) ========
        if status == "active":
            users_qs = users_qs.filter(is_active=True)
            employees_qs = employees_qs.filter(user__is_active=True)
        elif status == "inactive":
            users_qs = users_qs.filter(is_active=False)
            employees_qs = employees_qs.filter(user__is_active=False)

        # ======== تطبيق فلتر الفترة الزمنية على العقود (لحساب التعيينات/الخروج) ========
        date_from_obj = None
        date_to_obj = None

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                date_from_obj = None

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                date_to_obj = None

        if date_from_obj:
            contracts_qs = contracts_qs.filter(start_date__gte=date_from_obj)

        if date_to_obj:
            contracts_qs = contracts_qs.filter(start_date__lte=date_to_obj)

        # ======== الكروت الأربعة (metrics) باستخدام الـ QuerySets المفلترة ========
        total_employees = employees_qs.count()

        active_contracts = contracts_qs.filter(
            start_date__lte=today
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).count()

        # عدد الأقسام بناءً على الموظفين المفلترين (أدق من count لكل الأقسام)
        departments_count = (
            Department.objects.filter(employees__in=employees_qs).distinct().count()
        )

        pending_requests = leave_qs.filter(status="pending").count()

        # ======== Employees by Department (Bar chart) ========
        employees_by_department = [
            {
                "department": row["department__name"] or "Unassigned",
                "count": row["count"],
            }
            for row in employees_qs
                .values("department__name")
                .annotate(count=Count("id"))
                .order_by("department__name")
        ]

        # ======== Role Distribution (Pie chart) ========
        role_distribution = [
            {
                "role": row["role"],
                "count": row["count"],
            }
            for row in users_qs
                .values("role")
                .annotate(count=Count("id"))
                .order_by("role")
        ]

        # ======== Hires vs Exits (Line chart) ========
        hires = (
            contracts_qs
            .annotate(month=TruncMonth("start_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        exits = (
            contracts_qs
            .filter(end_date__isnull=False)
            .annotate(month=TruncMonth("end_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        hires_list = [
            {
                "month": row["month"].strftime("%Y-%m"),
                "count": row["count"],
            }
            for row in hires if row["month"] is not None
        ]

        exits_list = [
            {
                "month": row["month"].strftime("%Y-%m"),
                "count": row["count"],
            }
            for row in exits if row["month"] is not None
        ]

        # ======== Recent Activity (بدون فلترة زمنية حالياً) ========
        recent_activity = [
            {
                "user": (log.actor.get_full_name() or log.actor.username) if log.actor else "System",
                "action": log.action,
                "time": log.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for log in AuditLog.objects.select_related("actor")[:5]
        ]

        data = {
            "filters": {
                "department": department,
                "role": role,
                "status": status,
                "date_from": date_from,
                "date_to": date_to,
            },
            "metrics": {
                "total_employees": total_employees,
                "active_contracts": active_contracts,
                "departments": departments_count,
                "pending_requests": pending_requests,
            },
            "employees_by_department": employees_by_department,
            "role_distribution": role_distribution,
            "hires_vs_exits": {
                "hires": hires_list,
                "exits": exits_list,
            },
            "recent_activity": recent_activity,
        }

        return Response(data)

class DepartmentListCreateView(generics.ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class RoleListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/roles/      -> list roles
    POST /api/admin/roles/      -> create new role record
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/admin/roles/<id>/
    PUT    /api/admin/roles/<id>/
    PATCH  /api/admin/roles/<id>/
    DELETE /api/admin/roles/<id>/
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


# ================================
#   System Settings CRUD (Admin)
# ================================

class SystemSettingListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/settings/      -> list all settings
    POST /api/admin/settings/      -> create new setting
    """
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAdminUser]


class SystemSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/admin/settings/<id>/
    PUT    /api/admin/settings/<id>/
    PATCH  /api/admin/settings/<id>/
    DELETE /api/admin/settings/<id>/
    """
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAdminUser]
