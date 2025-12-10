from datetime import timedelta

from django.utils import timezone
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from manager.ai.serializers import SmartShiftSuggestionSerializer , WorkforcePlanningSerializer
from hr.attendance.models import Shift
from hr.employees.models import Employee, EmployeeStatus
from hr.attendance.models import AttendanceRecord, AttendanceStatus
from hr.org_structure.models import Company , Department


class BaseCompanyMixin:
    def get_company(self, request):
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None:
            return employee_profile.company
        return Company.objects.first()


class SmartShiftsView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = self.get_company(request)
        if not company:
            return Response([], status=200)

        department_id = request.query_params.get("department_id")

        days_param = request.query_params.get("days", "7")
        try:
            days = int(days_param)
        except ValueError:
            days = 7
        days = max(1, min(days, 14))  

        max_per_shift_param = request.query_params.get("max_per_shift")
        try:
            max_per_shift = int(max_per_shift_param) if max_per_shift_param else 3
        except ValueError:
            max_per_shift = 3
        max_per_shift = max(1, max_per_shift)

        employees_qs = Employee.objects.select_related("user", "department").filter(
            company=company,
            status=EmployeeStatus.ACTIVE,
        )

        if department_id:
            employees_qs = employees_qs.filter(department_id=department_id)

        employees = list(employees_qs)
        if not employees:
          
            return Response([], status=200)

        shifts_qs = Shift.objects.filter(is_active=True).order_by("start_time")
        shifts = list(shifts_qs)

        if not shifts:
          
            return Response([], status=200)

    
        suggestions = []
        employee_index = 0  
        today = timezone.now().date()

        for offset in range(days):
            date = today + timedelta(days=offset)
            day_label = date.strftime("%A")

            for shift in shifts:

                needed = min(max_per_shift, len(employees))
                assigned = []

                for _ in range(needed):
                    emp = employees[employee_index]
                    assigned.append(emp)
                    employee_index = (employee_index + 1) % len(employees)

                assigned_names = [
                    emp.user.get_full_name() or emp.user.username
                    for emp in assigned
                ]

                code_lower = shift.code.lower()
                if "morning" in code_lower or "am" in code_lower:
                    note = "Peak hours"
                elif "night" in code_lower or "pm" in code_lower:
                    note = "Low traffic"
                else:
                    note = "Regular load"

                suggestions.append(
                    {
                        "day": day_label,
                        "date": date,
                        "shift_name": shift.name,
                        "shift_code": shift.code,
                        "assigned_employees": assigned_names,
                        "notes": note,
                    }
                )

        serializer = SmartShiftSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)


class WorkforcePlanningView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = self.get_company(request)
        today = timezone.now().date()

        if not company:
            data = {
                "department_id": None,
                "department_name": "All Departments",
                "period": "this_month",
                "period_label": "This Month",
                "current_staff": 0,
                "required_staff": 0,
                "hiring_needed": 0,
                "skill_gap_index": 0.0,
                "recommendations": [],
            }
            serializer = WorkforcePlanningSerializer(data)
            return Response(serializer.data)

        dept_id = request.query_params.get("department_id")
        period = request.query_params.get("period", "this_month")

        if period == "next_quarter":
            period_label = "Next Quarter"
        elif period == "this_quarter":
            period_label = "This Quarter"
        else:
            period = "this_month"
            period_label = "This Month"

        department = None
        if dept_id:
            try:
                department = Department.objects.get(pk=dept_id, company=company)
            except Department.DoesNotExist:
                department = None

        employees_qs = Employee.objects.filter(
            company=company,
            status=EmployeeStatus.ACTIVE,
        )

        if department is not None:
            employees_qs = employees_qs.filter(department=department)

        current_staff = employees_qs.count()

        last_30 = today - timedelta(days=30)

        attendance_qs = AttendanceRecord.objects.filter(
            employee__in=employees_qs,
            date__gte=last_30,
            date__lte=today,
        )

        overtime_days = attendance_qs.filter(is_overtime=True).count()
        total_records = attendance_qs.count()

        if total_records > 0:
            overtime_ratio = overtime_days / total_records 
        else:
            overtime_ratio = 0.0

        extra_needed = 0
        if current_staff > 0:
            if overtime_ratio > 0.30:
                extra_needed = 3
            elif overtime_ratio > 0.15:
                extra_needed = 2
            elif overtime_ratio > 0.05:
                extra_needed = 1

        growth_factor = 0.0
        if period in ["this_quarter", "next_quarter"]:
            growth_factor = 0.10  
        elif period == "this_month":
            growth_factor = 0.05  

        base_required = int(round(current_staff * (1 + growth_factor)))
        required_staff = max(current_staff, base_required + extra_needed)

        hiring_needed = max(required_staff - current_staff, 0)

        skill_gap_index = 0.0
        if current_staff > 0:
            gap_component = min(20, hiring_needed * 4)      
            overtime_component = min(10, overtime_ratio * 40)   
            skill_gap_index = round(gap_component + overtime_component, 1)

        recommendations = []

        if hiring_needed >= 3:
            recommendations.append(
                {
                    "title": f"Hire {hiring_needed} new employees",
                    "description": (
                        "High workload and overtime detected. "
                        "Consider opening new positions to reduce burnout and stabilize capacity."
                    ),
                    "priority": "high",
                }
            )
        elif hiring_needed == 2:
            recommendations.append(
                {
                    "title": "Plan 2 new hires",
                    "description": (
                        "Team capacity is slightly below the required level. "
                        "Plan targeted hiring in the next cycle."
                    ),
                    "priority": "medium",
                }
            )
        elif hiring_needed == 1:
            recommendations.append(
                {
                    "title": "Backfill 1 critical role",
                    "description": (
                        "There is a small staffing gap. "
                        "Backfilling one key position will help maintain productivity."
                    ),
                    "priority": "medium",
                }
            )

        if overtime_ratio > 0.20:
            recommendations.append(
                {
                    "title": "Reduce overtime usage",
                    "description": (
                        "Overtime usage is high. "
                        "Review workload distribution and consider shifting tasks or hiring."
                    ),
                    "priority": "high",
                }
            )
        elif overtime_ratio > 0.05:
            recommendations.append(
                {
                    "title": "Monitor overtime patterns",
                    "description": (
                        "Overtime is moderate. "
                        "Monitor patterns and intervene early to avoid employee fatigue."
                    ),
                    "priority": "low",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "title": "Staffing level is healthy",
                    "description": (
                        "Current staffing appears sufficient for the selected period. "
                        "Continue to monitor workload and performance."
                    ),
                    "priority": "low",
                }
            )

        data = {
            "department_id": department.id if department else None,
            "department_name": department.name if department else "All Departments",
            "period": period,
            "period_label": period_label,
            "current_staff": current_staff,
            "required_staff": required_staff,
            "hiring_needed": hiring_needed,
            "skill_gap_index": skill_gap_index,
            "recommendations": recommendations,
        }

        serializer = WorkforcePlanningSerializer(data)
        return Response(serializer.data)