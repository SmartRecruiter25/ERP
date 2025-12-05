from django.db import models

from hr.org_structure.models import Company, Department, JobTitle, JobLevel
from hr.employees.models import Employee
from hr.resume.models import SkillLevel  


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full-time"
    PART_TIME = "part_time", "Part-time"
    CONTRACT = "contract", "Contract"
    INTERNSHIP = "internship", "Internship"
    FREELANCE = "freelance", "Freelance"


class JobRequirement(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="job_requirements",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_requirements",
    )
    job_title = models.ForeignKey(
        JobTitle,
        on_delete=models.PROTECT,
        related_name="job_requirements",
    )
    job_level = models.ForeignKey(
        JobLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_requirements",
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="مكان العمل (مدينة / دولة / Remote...).",
    )

    min_experience_years = models.PositiveIntegerField(
        default=0,
        help_text="الحد الأدنى لسنوات الخبرة المطلوبة.",
    )
    max_experience_years = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="الحد الأقصى لسنوات الخبرة (اختياري).",
    )

    headcount = models.PositiveIntegerField(
        default=1,
        help_text="عدد الموظفين المطلوبين لهذا المتطلب.",
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="وصف عام عن الوظيفة والمتطلبات الأخرى.",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_job_requirements",
        help_text="من قام بإضافة هذا المتطلب (غالباً HR / Manager).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company__name", "department__name", "job_title__title_name"]
        unique_together = (
            ("company", "department", "job_title", "job_level", "employment_type"),
        )

    def __str__(self):
        lvl = f" - {self.job_level.name}" if self.job_level else ""
        return f"{self.company.code} | {self.job_title.title_name}{lvl} ({self.employment_type})"


class JobRequirementSkill(models.Model):
    job_requirement = models.ForeignKey(
        JobRequirement,
        on_delete=models.CASCADE,
        related_name="skills",
    )

    skill_name = models.CharField(max_length=255)

    skill_level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,  
        default=SkillLevel.INTERMEDIATE,
    )

    is_mandatory = models.BooleanField(
        default=True,
        help_text="هل المهارة أساسية (Must-have) أم اختيارية (Nice-to-have)؟",
    )

    weight = models.PositiveIntegerField(
        default=1,
        help_text="أهمية المهارة في تقييم المرشحين (1–10 مثلاً).",
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["job_requirement", "-is_mandatory", "-weight", "skill_name"]
        unique_together = (("job_requirement", "skill_name"),)

    def __str__(self):
        flag = " (Mandatory)" if self.is_mandatory else " (Optional)"
        return f"{self.job_requirement} | {self.skill_name} [{self.skill_level}]{flag}"