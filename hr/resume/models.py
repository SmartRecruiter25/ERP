from django.db import models
from hr.employees.models import Employee


class ResumeSourceType(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    IMPORTED = "imported", "Imported/From External System"
    AI_GENERATED = "ai_generated", "AI Generated"


class ResumeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class Resume(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="resumes",
    )

    title = models.CharField(
        max_length=255,
        help_text="عنوان مختصر للسيرة مثل: Main CV 2025",
    )
    headline = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="جملة مختصرة عن الموظف (Professional Headline).",
    )

    summary = models.TextField(
        blank=True,
        null=True,
        help_text="ملخص نصي لمحتوى السيرة (اختياري).",
    )

    file = models.FileField(
        upload_to="resumes/%Y/%m/",
        blank=True,
        null=True,
        help_text="ملف السيرة الذاتية (PDF / DOCX...).",
    )

    source_type = models.CharField(
        max_length=20,
        choices=ResumeSourceType.choices,
        default=ResumeSourceType.UPLOADED,
    )

    language = models.CharField(
        max_length=10,
        default="en",
        help_text="لغة السيرة مثل: en, ar, fr...",
    )

    status = models.CharField(
        max_length=20,
        choices=ResumeStatus.choices,
        default=ResumeStatus.ACTIVE,
    )

    version = models.PositiveIntegerField(
        default=1,
        help_text="رقم الإصدار في حال حفظ عدة نسخ متتالية.",
    )

    skills_snapshot = models.TextField(
        blank=True,
        null=True,
        help_text="تمثيل JSON بسيط للمهارات وقت إنشاء السيرة (للأرشفة).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "status"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.title} (v{self.version})"

class SkillLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"
    EXPERT = "expert", "Expert"


class SkillProofType(models.TextChoices):
    FILE = "file", "File"
    LINK = "link", "Link"
    TEXT = "text", "Text / Description"


class SkillProofStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class SkillProof(models.Model):
  
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="skill_proofs",
    )

 
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="skill_proofs",
    )

    skill_name = models.CharField(max_length=255)
    skill_level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.INTERMEDIATE,
    )

    proof_type = models.CharField(
        max_length=10,
        choices=SkillProofType.choices,
        default=SkillProofType.FILE,
    )

    proof_file = models.FileField(
        upload_to="skill_proofs/%Y/%m/",
        blank=True,
        null=True,
    )
    proof_link = models.URLField(
        blank=True,
        null=True,
        help_text="رابط لمشروع GitHub أو LinkedIn أو غيره.",
    )
    proof_text = models.TextField(
        blank=True,
        null=True,
        help_text="شرح نصي أو توصيف للإثبات.",
    )

    status = models.CharField(
        max_length=20,
        choices=SkillProofStatus.choices,
        default=SkillProofStatus.PENDING,
    )


    verified_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_skill_proofs",
        help_text="الموظف (غالباً HR أو Manager) الذي اعتمد هذا الإثبات.",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "employee__employee_code", "skill_name"]
        indexes = [
            models.Index(fields=["employee", "skill_name"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.skill_name} ({self.status})"