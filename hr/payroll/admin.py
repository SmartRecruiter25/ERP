from django.contrib import admin
from .models import PayrollRun, PayrollItem


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "name",
        "year",
        "month",
        "period_start",
        "period_end",
        "status",
        "total_employees",
        "total_gross",
        "total_net",
        "created_at",
        "finalized_at",
    )
    list_filter = ("company", "status", "year", "month")
    search_fields = ("name", "company__name", "company__code")


@admin.register(PayrollItem)
class PayrollItemAdmin(admin.ModelAdmin):
    list_display = (
        "payroll_run",
        "employee",
        "basic_salary",
        "allowances",
        "overtime_pay",
        "deductions",
        "gross_salary",
        "net_salary",
        "currency",
    )
    list_filter = ("payroll_run__company", "currency")
    search_fields = ("employee__employee_code", "employee__user__username", "payroll_run__name")