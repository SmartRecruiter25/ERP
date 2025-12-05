from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from hr.employees.models import Employee


class Shift(models.Model):
    name = models.CharField(max_length=100) 
    code = models.CharField(max_length=20, unique=True)

    start_time = models.TimeField()  
    end_time = models.TimeField()    

    is_overnight = models.BooleanField(
        default=False,
        help_text="إذا كان الشفت يبدأ في يوم وينتهي في اليوم التالي (مثل 22:00 → 06:00)."
    )

    allowed_late_minutes = models.PositiveIntegerField(default=0)
    required_daily_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=8.0,
        help_text="عدد الساعات المتوقعة في اليوم (مثلاً 8 ساعات)."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        if not self.is_overnight and self.end_time <= self.start_time:
            raise ValidationError("لشفت غير الليلي يجب أن يكون وقت النهاية أكبر من وقت البداية.")

    def __str__(self):
        return f"{self.name} ({self.code})"


class EmployeeShiftAssignment(models.Model):
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="shift_assignments")
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="employee_assignments")

    start_date = models.DateField()
    end_date = models.DateField()

    is_primary = models.BooleanField(
        default=True,
        help_text="هل هذا هو الشفت الأساسي للموظف خلال هذه الفترة؟"
    )

    class Meta:
        ordering = ["employee__employee_code", "start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F("start_date")),
                name="shift_assignment_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} → {self.shift.code} ({self.start_date} → {self.end_date})"


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LATE = "late", "Late"
    ON_LEAVE = "on_leave", "On Leave"
    HOLIDAY = "holiday", "Holiday"
    REMOTE = "remote", "Remote"


class AttendanceRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()

    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        help_text="الشفت المتوقع لهذا اليوم إن وجد."
    )

    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )

    total_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="إجمالي ساعات العمل الفعلية في هذا اليوم."
    )

    is_overtime = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("employee", "date"),)
        ordering = ["-date", "employee__employee_code"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.date} ({self.status})"

    def clean(self):
       
        if self.check_out and not self.check_in:
            raise ValidationError("لا يمكن تسجيل وقت الخروج بدون وقت الدخول.")

       
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError("وقت الخروج يجب أن يكون بعد وقت الدخول.")

    def calculate_total_hours(self):
        
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            hours = delta.total_seconds() / 3600.0
            return round(hours, 2)
        return 0

    def save(self, *args, **kwargs):
       
        self.full_clean()

       
        self.total_hours = self.calculate_total_hours()

        
        if self.shift and self.total_hours > float(self.shift.required_daily_hours):
            self.is_overtime = True
        else:
            self.is_overtime = False

        super().save(*args, **kwargs)