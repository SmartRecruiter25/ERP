from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from manager.payroll.serializers import (
    PayrollRunSerializer,
    PayrollSummarySerializer,
)
from hr.payroll.models import PayrollRun, PayrollRunStatus
from hr.org_structure.models import Company


class BaseCompanyMixin:
    def get_company(self, request):
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None:
            return employee_profile.company
        return Company.objects.first()


class PayrollSummaryView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated]

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

        unpaid_qs = runs_qs.filter(
            status__in=[PayrollRunStatus.DRAFT, PayrollRunStatus.APPROVED]
        )
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            return Response([], status=200)

        limit_param = request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param else 10
        except ValueError:
            limit = 10

        runs_qs = (
            PayrollRun.objects
            .filter(company=company)
            .order_by("-year", "-month")[:limit]
        )

        serializer = PayrollRunSerializer(runs_qs, many=True)
        return Response(serializer.data)