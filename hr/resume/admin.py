from django.contrib import admin
from .models import Resume, SkillProof


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "title",
        "source_type",
        "language",
        "status",
        "version",
        "created_at",
    )
    list_filter = ("source_type", "status", "language", "employee__company")
    search_fields = ("title", "employee__employee_code", "employee__user__username")


@admin.register(SkillProof)
class SkillProofAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "skill_name",
        "skill_level",
        "proof_type",
        "status",
        "verified_by",
        "verified_at",
        "created_at",
    )
    list_filter = ("skill_level", "proof_type", "status", "employee__company")
    search_fields = ("employee__employee_code", "employee__user__username", "skill_name")