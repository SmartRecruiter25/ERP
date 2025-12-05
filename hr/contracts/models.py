from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from hr.employees.models import Employee

class ContractType(models.TextChoices):
    PERMANENT = "permanent", "Permanent"
    TEMPORARY = "temporary", "Temporary"
    INTERNSHIP = "internship", "Internship"
    PARTTIME = "parttime", "Part-time"

class ContractStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    RENEWED = "renewed", "Renewed"
    TERMINATED = "terminated", "Terminated"

class EmployeeContract(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="contracts")
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.PERMANENT)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.ACTIVE)

    title = models.CharField(max_length=255, blank=True, null=True)  
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    file = models.FileField(upload_to="contracts/%Y/%m/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        
        constraints = [
            models.CheckConstraint(check=models.Q(end_date__gt=models.F("start_date")), name="contract_end_after_start"),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} | {self.contract_type} | {self.start_date}→{self.end_date}"

    @property
    def is_active(self):
        today = timezone.now().date()
        return self.status == ContractStatus.ACTIVE and self.start_date <= today <= self.end_date

    def clean(self):
       
        overlaps = EmployeeContract.objects.filter(employee=self.employee).exclude(pk=self.pk).filter(
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        )
        if overlaps.exists():
            raise ValidationError("يوجد عقد آخر تتداخل فترته مع هذه الفترة لنفس الموظف.")

       
        if self.end_date < timezone.now().date() and self.status == ContractStatus.ACTIVE:
            self.status = ContractStatus.EXPIRED

    def save(self, *args, **kwargs):
        self.full_clean()  
        super().save(*args, **kwargs)


class ContractRenewLog(models.Model):
    contract = models.ForeignKey(EmployeeContract, on_delete=models.CASCADE, related_name="renew_logs")
    renew_date = models.DateField()
    old_end_date = models.DateField()
    new_end_date = models.DateField()
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-renew_date"]
        constraints = [
            models.CheckConstraint(check=models.Q(new_end_date__gt=models.F("old_end_date")), name="renew_end_after_old"),
        ]

    def __str__(self):
        return f"Renew {self.contract_id} on {self.renew_date} → {self.new_end_date}"