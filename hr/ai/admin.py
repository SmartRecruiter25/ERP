from django.contrib import admin
from .models import ContractAlert, ManpowerForecast


@admin.register(ContractAlert)
class ContractAlertAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "alert_type",
        "alert_date",
        "is_read",
        "is_resolved",
        "created_at",
    )
    list_filter = ("alert_type", "is_read", "is_resolved", "employee__company")
    search_fields = ("employee__employee_code", "employee__user__username")


@admin.register(ManpowerForecast)
class ManpowerForecastAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "department",
        "year",
        "month",
        "current_headcount",
        "required_headcount",
        "gap",
        "ai_generated",
        "generated_at",
    )
    list_filter = ("company", "department", "year", "month", "ai_generated")
    search_fields = ("company__name", "company__code", "department__name")