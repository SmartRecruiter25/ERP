from django.contrib import admin
from .models import EmployeeContract, ContractRenewLog

@admin.register(EmployeeContract)
class EmployeeContractAdmin(admin.ModelAdmin):
    list_display = ("employee", "contract_type", "start_date", "end_date", "status", "base_salary", "currency", "is_active")
    list_filter = ("contract_type", "status", "employee__company")
    search_fields = ("employee__employee_code", "employee__user__username")

@admin.register(ContractRenewLog)
class ContractRenewLogAdmin(admin.ModelAdmin):
    list_display = ("contract", "renew_date", "old_end_date", "new_end_date")
    search_fields = ("contract__employee__employee_code",)