from django.db import models
from django.utils import timezone

from hr.employees.models import Employee
from hr.org_structure.models import Company  


class LeaveType(models.TextChoices):
    ANNUAL = "annual", "Annual Leave"
    SICK = "sick", "Sick Leave"
    UNPAID = "unpaid", "Unpaid Leave"
    MATERNITY = "maternity", "Maternity Leave"
    EMERGENCY = "emergency", "Emergency Leave"
    OTHER = "other", "Other"


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class LeaveRequest(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices,
        default=LeaveType.ANNUAL,
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_half_day = models.BooleanField(
        default=False,
        help_text="إذا كانت الإجازة نصف يوم فقط."
    )

    reason = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
    )

    approver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
        help_text="الموظف (Manager/HR) الذي وافق/رفض الطلب."
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        help_text="سبب إلغاء الطلب إن تم إلغاؤه."
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F("start_date")),
                name="leave_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type} ({self.start_date} → {self.end_date})"

    @property
    def total_days(self):
        if self.start_date and self.end_date:
            days = (self.end_date - self.start_date).days + 1
            return 0.5 if self.is_half_day else days
        return 0

    def approve(self, approver: Employee):
        self.status = LeaveStatus.APPROVED
        self.approver = approver
        self.approved_at = timezone.now()
        self.save()

    def reject(self, approver: Employee, reason: str = ""):
        self.status = LeaveStatus.REJECTED
        self.approver = approver
        self.approved_at = timezone.now()
        if reason:
            self.cancellation_reason = reason
        self.save()

class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class OvertimeRequest(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="overtime_requests",
    )
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    reason = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_overtime_requests",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Overtime {self.employee.employee_code} - {self.date} ({self.hours}h)"


class ExpenseCategory(models.TextChoices):
    TRAVEL = "travel", "Travel"
    MEALS = "meals", "Meals"
    SUPPLIES = "supplies", "Supplies"
    OTHER = "other", "Other"


class ExpenseRequest(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="expense_requests",
    )
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER,
    )
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")

    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_expense_requests",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Expense {self.employee.employee_code} - {self.amount} {self.currency}"


class HRFormType(models.TextChoices):
    CERTIFICATE = "certificate", "Employment Certificate"
    UPDATE_INFO = "update_info", "Update Personal Info"
    OTHER = "other", "Other"


class HRFormRequest(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="hr_form_requests",
    )
    form_type = models.CharField(
        max_length=30,
        choices=HRFormType.choices,
        default=HRFormType.OTHER,
    )
    subject = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_hr_form_requests",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"HR Form {self.employee.employee_code} - {self.subject}"

class AnnouncementCategory(models.TextChoices):
    GENERAL = "general", "General"
    HOLIDAY = "holiday", "Holiday"
    POLICY = "policy", "Policy"
    REMINDER = "reminder", "Reminder"
    OTHER = "other", "Other"


class Announcement(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, null=True)

    category = models.CharField(
        max_length=20,
        choices=AnnouncementCategory.choices,
        default=AnnouncementCategory.GENERAL,
    )

    company = models.ForeignKey(        
        Company,
        on_delete=models.CASCADE,
        related_name="announcements",
        null=True,
        blank=True,
        help_text="إذا تُركت فارغة → الإعلان عام لكل الشركات.",
    )

    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(
        default=False,
        help_text="إذا كان True يظهر في أعلى القائمة."
    )

    valid_from = models.DateField(
        null=True,
        blank=True,
        help_text="تاريخ بداية ظهور الإعلان (اختياري).",
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="تاريخ نهاية ظهور الإعلان (اختياري).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title

    def is_currently_visible(self, today=None):
        if not self.is_active:
            return False

        if today is None:
            today = timezone.now().date()

        if self.valid_from and self.valid_from > today:
            return False

        if self.valid_to and self.valid_to < today:
            return False

        return True