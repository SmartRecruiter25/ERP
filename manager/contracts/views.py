from django.utils import timezone
from rest_framework.views import APIView
from django.db import models
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from manager.contracts.serializers import (
    ContractListSerializer,
    ContractsSummarySerializer,
)

from hr.contracts.models import EmployeeContract, ContractStatus
from hr.org_structure.models import Company
from accounts.permissions import IsAdminOrHR

class BaseCompanyMixin:
    def get_company(self, request):
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None:
            return employee_profile.company
        return Company.objects.first()


class ContractsSummaryView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated , IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            data = {
                "total_contracts": 0,
                "active_contracts": 0,
                "expiring_30_days": 0,
                "expired_contracts": 0,
            }
            serializer = ContractsSummarySerializer(data)
            return Response(serializer.data)

        today = timezone.now().date()
        in_30_days = today + timezone.timedelta(days=30)

        qs = EmployeeContract.objects.filter(employee__company=company)

        total_contracts = qs.count()
        active_contracts = qs.filter(status=ContractStatus.ACTIVE).count()

        expiring_30_days = qs.filter(
            status=ContractStatus.ACTIVE,
            end_date__gte=today,
            end_date__lte=in_30_days,
        ).count()

        expired_contracts = qs.filter(
            status=ContractStatus.EXPIRED
        ).count()

        data = {
            "total_contracts": total_contracts,
            "active_contracts": active_contracts,
            "expiring_30_days": expiring_30_days,
            "expired_contracts": expired_contracts,
        }

        serializer = ContractsSummarySerializer(data)
        return Response(serializer.data)


class ContractsListView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated , IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            return Response([], status=200)

        today = timezone.now().date()
        qs = EmployeeContract.objects.filter(employee__company=company).select_related(
            "employee__user", "employee__department", "employee__job_title"
        )

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        expiring_in = request.query_params.get("expiring_in")
        if expiring_in:
            try:
                days = int(expiring_in)
                to_date = today + timezone.timedelta(days=days)
                qs = qs.filter(
                    end_date__gte=today,
                    end_date__lte=to_date,
                    status=ContractStatus.ACTIVE,
                )
            except ValueError:
                pass  

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(employee__employee_code__icontains=search)
                | models.Q(employee__user__username__icontains=search)
                | models.Q(employee__user__first_name__icontains=search)
                | models.Q(employee__user__last_name__icontains=search)
            )

        serializer = ContractListSerializer(qs, many=True)
        return Response(serializer.data)