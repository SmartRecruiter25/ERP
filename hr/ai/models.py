from django.db import models
from django.utils import timezone

from hr.employees.models import Employee
from hr.org_structure.models import Company, Department
from hr.contracts.models import EmployeeContract

class ContractAlertType(models.TextChoices):
    EXPIRY_SOON = "expiry_soon", "Contract Expiry Soon"
    EXPIRED = "expired", "Contract Expired"
    NO_CONTRACT = "no_contract", "No Active Contract"
    PROBATION_END = "probation_end", "Probation Period Ending"


class ContractAlert(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="contract_alerts",
    )
    contract = models.ForeignKey(
        EmployeeContract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="العقد المرتبط بهذا التنبيه إن وجد.",
    )

    alert_type = models.CharField(
        max_length=30,
        choices=ContractAlertType.choices,
    )

    alert_date = models.DateTimeField(default=timezone.now)

    message = models.TextField(
        help_text="نص التنبيه الذي سيتم عرضه للمستخدم أو المانجر.",
    )

    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)

    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-alert_date"]
        indexes = [
            models.Index(fields=["employee", "alert_type"]),
            models.Index(fields=["is_read", "is_resolved"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.alert_type} ({self.alert_date.date()})"

    def mark_read(self):
        self.is_read = True
        self.save()

    def mark_resolved(self):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()

class ManpowerForecast(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="manpower_forecasts",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manpower_forecasts",
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(help_text="1 = January, 12 = December")

    current_headcount = models.PositiveIntegerField(
        default=0,
        help_text="عدد الموظفين الحالي في هذا القسم/الشركة.",
    )
    required_headcount = models.PositiveIntegerField(
        default=0,
        help_text="عدد الموظفين المطلوب حسب التنبؤ.",
    )

    gap = models.IntegerField(
        default=0,
        help_text="required - current (موجب = نقص، سالب = زيادة).",
    )

    ai_generated = models.BooleanField(
        default=True,
        help_text="هل هذه التوقعات مولدة بالـ AI أم مدخلة يدويًا.",
    )

    model_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="رقم/اسم نسخة نموذج الذكاء الاصطناعي المستخدم.",
    )

    notes = models.TextField(blank=True, null=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "company__name", "department__name"]
        unique_together = (("company", "department", "year", "month"),)

    def __str__(self):
        dept = self.department.name if self.department else "All Departments"
        return f"{self.company.code} - {dept} ({self.year}/{self.month})"

    def save(self, *args, **kwargs):
        self.gap = int(self.required_headcount) - int(self.current_headcount)
        super().save(*args, **kwargs)