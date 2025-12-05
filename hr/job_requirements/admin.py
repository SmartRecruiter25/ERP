from django.contrib import admin
from .models import JobRequirement, JobRequirementSkill


class JobRequirementSkillInline(admin.TabularInline):
    model = JobRequirementSkill
    extra = 1


@admin.register(JobRequirement)
class JobRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "department",
        "job_title",
        "job_level",
        "employment_type",
        "headcount",
        "min_experience_years",
        "max_experience_years",
        "is_active",
        "created_at",
    )
    list_filter = (
        "company",
        "department",
        "job_title",
        "job_level",
        "employment_type",
        "is_active",
    )
    search_fields = (
        "job_title__title_name",
        "department__name",
        "company__name",
        "company__code",
    )
    inlines = [JobRequirementSkillInline]


@admin.register(JobRequirementSkill)
class JobRequirementSkillAdmin(admin.ModelAdmin):
    list_display = (
        "job_requirement",
        "skill_name",
        "skill_level",
        "is_mandatory",
        "weight",
    )
    list_filter = ("skill_level", "is_mandatory")
    search_fields = ("skill_name", "job_requirement__job_title__title_name")