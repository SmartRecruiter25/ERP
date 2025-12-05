from django.db import models
from django.conf import settings
from hr.org_structure.models import Company, Department, JobTitle, JobLevel

class EmployeeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    RESIGNED = "resigned", "Resigned"
    TERMINATED = "terminated", "Terminated"

class Employee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='employee_profile')
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='employees')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    job_title = models.ForeignKey(JobTitle, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')

    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')

    employee_code = models.CharField(max_length=30, unique=True)  
    hire_date = models.DateField()
    status = models.CharField(max_length=20, choices=EmployeeStatus.choices, default=EmployeeStatus.ACTIVE)

    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")

    performance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Performance score (0–100) used in Manager dashboard."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company__name", "department__name", "user__username"]
        indexes = [
            models.Index(fields=["employee_code"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user.get_username()} [{self.employee_code}]"


class EmployeeDocument(models.Model):
    class DocType(models.TextChoices):
        ID = "id", "National ID/Passport"
        CONTRACT = "contract", "Contract"
        CERTIFICATE = "certificate", "Certificate"
        CV = "cv", "CV / Resume"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="employee_docs/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.title}"