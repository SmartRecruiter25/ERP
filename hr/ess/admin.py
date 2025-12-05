from django.contrib import admin
from .models import LeaveRequest , Announcement


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "is_half_day",
        "status",
        "approver",
        "created_at",
    )
    list_filter = ("leave_type", "status", "employee__company")
    search_fields = ("employee__employee_code", "employee__user__username")

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "company",
        "is_active",
        "is_pinned",
        "valid_from",
        "valid_to",
        "created_at",
    )
    list_filter = ("category", "is_active", "company")
    search_fields = ("title", "body")