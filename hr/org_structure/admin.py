from django.contrib import admin
from .models import(
 Company, 
 Department,
  JobTitle, 
  JobLevel, 
  CompanyNews , 
  CompanyNotification , )

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "email", "phone", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "email", "phone")

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "parent", "manager")
    list_filter = ("company",)
    search_fields = ("code", "name", "company__name")

@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ("title_name",)
    search_fields = ("title_name",)

@admin.register(JobLevel)
class JobLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "rank")
    list_filter = ("name",)

@admin.register(CompanyNews)
class CompanyNewsAdmin(admin.ModelAdmin):
    list_display = ("company", "title", "date", "is_pinned", "created_at")
    list_filter = ("company", "is_pinned", "date")
    search_fields = ("title", "company__name", "company__code")


@admin.register(CompanyNotification)
class CompanyNotificationAdmin(admin.ModelAdmin):
    list_display = ("company", "role", "priority", "is_active", "starts_at", "ends_at", "created_at")
    list_filter = ("company", "role", "priority", "is_active")
    search_fields = ("message",)
