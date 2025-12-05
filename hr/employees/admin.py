from django.contrib import admin
from .models import Employee, EmployeeDocument

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "user", "company", "department", "job_title", "job_level", "status", "hire_date", "base_salary", "currency")
    list_filter = ("company", "department", "status")
    search_fields = ("employee_code", "user__username", "user__email")

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "doc_type", "title", "uploaded_at")
    list_filter = ("doc_type",)
    search_fields = ("employee__employee_code", "title")  