from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

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
        max_digits=4,
        decimal_places=2,
        default=Decimal("8.00"),
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

    is_primary = models.BooleanField(default=True)

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


def _local_dt(day, t):
    naive = datetime.combine(day, t)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class AttendanceRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()

    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )

    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )

    # ✅ Payroll metrics
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    late_minutes = models.PositiveIntegerField(default=0)
    early_leave_minutes = models.PositiveIntegerField(default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

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

    def _scheduled_window(self):
      
        if not self.shift:
            return None, None

        start = _local_dt(self.date, self.shift.start_time)

        if self.shift.is_overnight:
            end = _local_dt(self.date, self.shift.end_time) + timedelta(days=1)
        else:
            end = _local_dt(self.date, self.shift.end_time)

        return start, end

    def _round_2(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_total_hours(self) -> Decimal:
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            hours = Decimal(str(delta.total_seconds())) / Decimal("3600")
            return self._round_2(hours)
        return Decimal("0.00")

    def calculate_late_early_overtime(self):
       
        if not self.shift or not self.check_in:
            return 0, 0, Decimal("0.00")

        scheduled_start, scheduled_end = self._scheduled_window()
        if not scheduled_start or not scheduled_end:
            return 0, 0, Decimal("0.00")

        
        allowed = timedelta(minutes=int(self.shift.allowed_late_minutes or 0))
        late_td = (self.check_in - scheduled_start) - allowed
        late_minutes = max(0, int(late_td.total_seconds() // 60))

        early_minutes = 0
        overtime_hours = Decimal("0.00")

        if self.check_out:
            if self.check_out < scheduled_end:
                early_td = (scheduled_end - self.check_out)
                early_minutes = max(0, int(early_td.total_seconds() // 60))
            elif self.check_out > scheduled_end:
                ot_td = (self.check_out - scheduled_end)
                overtime_hours = self._round_2(Decimal(str(ot_td.total_seconds())) / Decimal("3600"))

       
        total_hours = self.calculate_total_hours()
        req = Decimal(str(self.shift.required_daily_hours or Decimal("0.00")))
        if req > 0 and total_hours > req:
            overtime_hours = max(overtime_hours, self._round_2(total_hours - req))

        
        if late_minutes > 0 and self.status == AttendanceStatus.PRESENT:
            self.status = AttendanceStatus.LATE

        return late_minutes, early_minutes, overtime_hours

    def save(self, *args, **kwargs):
        self.full_clean()

        self.total_hours = self.calculate_total_hours()
        late_m, early_m, ot_h = self.calculate_late_early_overtime()

        self.late_minutes = late_m
        self.early_leave_minutes = early_m
        self.overtime_hours = ot_h

        self.is_overtime = bool(self.overtime_hours and self.overtime_hours > Decimal("0.00"))

        super().save(*args, **kwargs)