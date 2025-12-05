from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

import secrets
import string
from manager.people.serializers import (
    EmployeeListSerializer,
    PeopleHubSummarySerializer
)

from hr.employees.models import  ( Employee,
 EmployeeStatus ,
)
from .serializers import EmployeeCreateSerializer   
from hr.ess.models import LeaveRequest, LeaveStatus
from hr.org_structure.models import Company
from hr.org_structure.models import Department


from hr.org_structure.models import Department, Company  

class PeopleHubSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        employee_profile = getattr(request.user, "employee_profile", None)

        if employee_profile is not None:
            company = employee_profile.company
        else:
            company = Company.objects.first()
            if company is None:
                data = {
                    "total_employees": 0,
                    "active_employees": 0,
                    "on_leave_today": 0,
                    "departments_count": 0,
                }
                serializer = PeopleHubSummarySerializer(data)
                return Response(serializer.data)

        total_employees = Employee.objects.filter(company=company).count()

        active_employees = Employee.objects.filter(
            company=company,
            status=EmployeeStatus.ACTIVE
        ).count()

        on_leave_today = Employee.objects.filter(
            company=company,
            leave_requests__status=LeaveStatus.APPROVED,
            leave_requests__start_date__lte=today,
            leave_requests__end_date__gte=today,
        ).distinct().count()

        departments_count = Department.objects.filter(company=company).count()

        data = {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "on_leave_today": on_leave_today,
            "departments_count": departments_count,
        }

        serializer = PeopleHubSummarySerializer(data)
        return Response(serializer.data)


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        employee_profile = getattr(request.user, "employee_profile", None)

        if employee_profile is not None:
            company = employee_profile.company
        else:
            company = Company.objects.first()
            if company is None:
                return Response([], status=200)

        employees = Employee.objects.filter(company=company).select_related(
            "user", "department", "job_title"
        )

        serializer = EmployeeListSerializer(
            employees,
            many=True,
            context={"today": today}
        )

        return Response(serializer.data)

class EmployeeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_company(self, request):
        emp_profile = getattr(request.user, "employee_profile", None)
        if emp_profile is not None:
            return emp_profile.company
        return Company.objects.first()

    def post(self, request, *args, **kwargs):
        company = self.get_company(request)
        if not company:
            return Response(
                {"detail": "No company configured for this request."},
                status=400,
            )

        serializer = EmployeeCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        User = get_user_model()

        full_name = data["full_name"].strip()
        email = data["email"].lower()

        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        alphabet = string.ascii_letters + string.digits
        raw_password = ''.join(secrets.choice(alphabet) for _ in range(10))
 
        user = User.objects.create_user(
            username=email,     
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=raw_password,
            role="employee",
        )

        existing_count = Employee.objects.filter(company=company).count() + 1
        employee_code = f"{company.code}-{existing_count:04d}"

        employee = Employee.objects.create(
            user=user,
            company=company,
            department=data.get("department"),
            job_title=data.get("job_title"),
            job_level=None,
            manager=None,
            employee_code=employee_code,
            hire_date=data["start_date"],
            status=data.get("status") or EmployeeStatus.ACTIVE,
            base_salary=0,
            currency="USD",
        )

        response_data = {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "name": full_name,
            "email": email,
            "job_title": employee.job_title.title_name if employee.job_title else None,
            "department": employee.department.name if employee.department else None,
            "status": employee.status,
            "hire_date": employee.hire_date,
            "initial_password": raw_password,
        }

        return Response(response_data, status=201)