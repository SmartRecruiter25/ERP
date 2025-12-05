from django.contrib import admin
from .models import Shift, EmployeeShiftAssignment, AttendanceRecord


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "start_time", "end_time", "is_overnight", "allowed_late_minutes", "required_daily_hours", "is_active")
    list_filter = ("is_active", "is_overnight")
    search_fields = ("code", "name")


@admin.register(EmployeeShiftAssignment)
class EmployeeShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "shift", "start_date", "end_date", "is_primary")
    list_filter = ("shift", "is_primary")
    search_fields = ("employee__employee_code", "employee__user__username")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "shift", "status", "check_in", "check_out", "total_hours", "is_overtime")
    list_filter = ("status", "shift", "employee__company")
    search_fields = ("employee__employee_code", "employee__user__username")