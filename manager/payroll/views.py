from django.db.models import Sum
from django.db import IntegrityError, transaction

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404

from manager.payroll.serializers import (
    PayrollRunSerializer,
    PayrollSummarySerializer,
    PayrollRunCreateSerializer,
)

from hr.payroll.models import PayrollRun, PayrollRunStatus
from hr.org_structure.models import Company
from accounts.permissions import IsAdminOrHR
from hr.employees.models import Employee, EmployeeStatus
from hr.payroll.services import generate_payroll_items


class BaseCompanyMixin:
    def get_company(self, request):
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None:
            return employee_profile.company
        return Company.objects.first()


class PayrollSummaryView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)

        if not company:
            data = {
                "total_runs": 0,
                "last_run_total_net": 0,
                "last_run_status": None,
                "last_run_period": None,
                "employees_in_last_run": 0,
                "unpaid_total": 0,
            }
            serializer = PayrollSummarySerializer(data)
            return Response(serializer.data)

        runs_qs = PayrollRun.objects.filter(company=company).order_by("-year", "-month")

        total_runs = runs_qs.count()
        last_run = runs_qs.first()

        if last_run:
            last_run_total_net = last_run.total_net
            last_run_status = last_run.status
            last_run_period = f"{last_run.month}/{last_run.year}"
            employees_in_last_run = last_run.total_employees
        else:
            last_run_total_net = 0
            last_run_status = None
            last_run_period = None
            employees_in_last_run = 0

        unpaid_qs = runs_qs.filter(status__in=[PayrollRunStatus.DRAFT, PayrollRunStatus.APPROVED])
        unpaid_total = unpaid_qs.aggregate(total=Sum("total_net"))["total"] or 0

        data = {
            "total_runs": total_runs,
            "last_run_total_net": last_run_total_net,
            "last_run_status": last_run_status,
            "last_run_period": last_run_period,
            "employees_in_last_run": employees_in_last_run,
            "unpaid_total": unpaid_total,
        }

        serializer = PayrollSummarySerializer(data)
        return Response(serializer.data)


class PayrollRunListView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            return Response([], status=200)

        limit_param = request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param else 10
        except ValueError:
            limit = 10

        runs_qs = PayrollRun.objects.filter(company=company).order_by("-year", "-month")[:limit]
        serializer = PayrollRunSerializer(runs_qs, many=True)
        return Response(serializer.data)


class PayrollRunCreateView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def post(self, request):
        company = self.get_company(request)
        if not company:
            return Response({"detail": "Company not found."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PayrollRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        month = data["month"]
        period_start = data["period_start"]
        period_end = data["period_end"]

        name = f"{period_start.strftime('%B')} {year} Payroll"

        try:
            run = PayrollRun.objects.create(
                company=company,
                name=name,
                year=year,
                month=month,
                period_start=period_start,
                period_end=period_end,
                status=PayrollRunStatus.DRAFT,
            )
        except IntegrityError:
            return Response(
                {"detail": "Payroll run already exists for this company and month."},
                status=status.HTTP_409_CONFLICT,
            )

        out = PayrollRunSerializer(run)
        return Response(out.data, status=status.HTTP_201_CREATED)


class PayrollRunGenerateItemsView(BaseCompanyMixin, APIView):
   
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def post(self, request, pk):
        company = self.get_company(request)
        if not company:
            return Response({"detail": "Company not found."}, status=status.HTTP_400_BAD_REQUEST)

        run = get_object_or_404(PayrollRun, pk=pk, company=company)

        if run.status != PayrollRunStatus.DRAFT:
            return Response(
                {"detail": "You can only generate items when run is DRAFT."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        
        employees_qs = Employee.objects.filter(company=company, status=EmployeeStatus.ACTIVE)

       
        with transaction.atomic():
            result = generate_payroll_items(run, employees_qs=employees_qs)

        return Response(result, status=status.HTTP_200_OK)