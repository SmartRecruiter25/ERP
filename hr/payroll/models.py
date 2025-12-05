# hr/payroll/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from hr.org_structure.models import Company
from hr.employees.models import Employee


class PayrollRunStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    POSTED = "posted", "Posted"
    PAID = "paid", "Paid"


class PayrollRun(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="payroll_runs",
    )

    name = models.CharField(
        max_length=255,
        help_text="اسم الدورة مثل: January 2026 Payroll"
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(help_text="1 = January, 12 = December")

    period_start = models.DateField()
    period_end = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=PayrollRunStatus.choices,
        default=PayrollRunStatus.DRAFT,
    )

    total_employees = models.PositiveIntegerField(default=0)
    total_gross = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="مجموع الرواتب الإجمالي قبل الخصومات."
    )
    total_net = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="مجموع صافي الرواتب بعد الخصومات."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "-month", "company__name"]
        unique_together = (("company", "year", "month"),)
        constraints = [
            models.CheckConstraint(
                check=models.Q(period_end__gte=models.F("period_start")),
                name="payroll_period_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.company.code} - {self.name}"

    def clean(self):
        if self.period_start and self.period_end:
            if self.period_start > self.period_end:
                raise ValidationError(
                    "تاريخ نهاية دورة الرواتب يجب أن يكون بعد تاريخ البداية."
                )

    def recalculate_totals(self):
        items = self.items.all()
        self.total_employees = items.count()
        self.total_gross = sum((i.gross_salary for i in items), 0)
        self.total_net = sum((i.net_salary for i in items), 0)
        super().save(update_fields=["total_employees", "total_gross", "total_net"])


class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="items",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="payroll_items",
    )

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="مجموع البدلات (سكن، مواصلات، ...)."
    )
    overtime_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="بدل الساعات الإضافية."
    )
    deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="الخصومات (تأخير، غياب، تأمينات، ...)."
    )

    gross_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="الراتب الإجمالي قبل الخصومات."
    )
    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="الصافي بعد الخصومات."
    )

    currency = models.CharField(max_length=10, default="USD")

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payroll_run__year", "payroll_run__month", "employee__employee_code"]
        unique_together = (("payroll_run", "employee"),)
        indexes = [
            models.Index(fields=["payroll_run", "employee"]),
        ]

    def __str__(self):
        return f"{self.payroll_run} - {self.employee.employee_code}"

    def calculate_gross(self):
        return (self.basic_salary or 0) + (self.allowances or 0) + (self.overtime_pay or 0)

    def calculate_net(self):
        gross = self.calculate_gross()
        return gross - (self.deductions or 0)

    def save(self, *args, **kwargs):

        self.gross_salary = self.calculate_gross()
        self.net_salary = self.calculate_net()
        self.full_clean()
        super().save(*args, **kwargs)

        self.payroll_run.recalculate_totals()

        from hr.payroll.models import Payslip, PayslipStatus 

        if self.payroll_run.status in {
            PayrollRunStatus.APPROVED,
            PayrollRunStatus.POSTED,
            PayrollRunStatus.PAID,
        }:
            slip_status = PayslipStatus.PAID
        else:
            slip_status = PayslipStatus.PENDING

        Payslip.objects.update_or_create(
            employee=self.employee,
            year=self.payroll_run.year,
            month=self.payroll_run.month,
            defaults={
                "payroll_run": self.payroll_run,
                "payroll_item": self,
                "net_amount": self.net_salary,
                "currency": self.currency,
                "status": slip_status,
            },
        )


class PayslipStatus(models.TextChoices):
    PAID = "paid", "Paid"
    PENDING = "pending", "Pending"
    CANCELLED = "cancelled", "Cancelled"


class Payslip(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="payslips",
    )

    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.SET_NULL,
        related_name="payslips",
        null=True,
        blank=True,
    )

    payroll_item = models.OneToOneField(
        PayrollItem,
        on_delete=models.SET_NULL,
        related_name="payslip",
        null=True,
        blank=True,
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField() 

    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")

    status = models.CharField(
        max_length=20,
        choices=PayslipStatus.choices,
        default=PayslipStatus.PAID,
    )

    file = models.FileField(
        upload_to="payslips/",
        blank=True,
        null=True,
        help_text="ملف PDF لكشف الراتب (اختياري).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = (("employee", "year", "month"),)

    def __str__(self):
        return f"Payslip {self.employee} - {self.year}-{self.month} ({self.net_amount} {self.currency})"