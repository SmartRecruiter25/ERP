from django.db import models
from django.utils import timezone

class Company(models.Model):
    code = models.CharField(max_length=20, unique=True)  
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.code}]"


class Department(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    manager = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')

    class Meta:
        unique_together = (('company', 'code'), ('company', 'name'))
        ordering = ['company__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.company.code})"


class JobTitle(models.Model):
    title_name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['title_name']

    def __str__(self):
        return self.title_name


class JobLevel(models.Model):
    class LevelName(models.TextChoices):
        INTERN = 'Intern', 'Intern'
        JUNIOR = 'Junior', 'Junior'
        MID = 'Mid', 'Mid'
        SENIOR = 'Senior', 'Senior'
        LEAD = 'Lead', 'Lead'
        MANAGER = 'Manager', 'Manager'

    name = models.CharField(max_length=50, choices=LevelName.choices)
    rank = models.PositiveIntegerField(default=1, help_text="Higher rank means higher seniority")

    class Meta:
        unique_together = (('name', 'rank'),)
        ordering = ['rank', 'name']

    def __str__(self):
        return f"{self.name} (Rank {self.rank})"

class CompanyNews(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="news",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    date = models.DateField()
    is_pinned = models.BooleanField(
        default=False,
        help_text="إذا true يظهر في الأعلى كخبر مهم."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-date", "-created_at"]

    def __str__(self):
        return f"{self.company.code} - {self.title}"

class NotificationPriority(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"

class NotificationRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    HR = "hr", "HR"
    MANAGER = "manager", "Manager"
    EMPLOYEE = "employee", "Employee"
    ALL = "all", "All"

class CompanyNotification(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    role = models.CharField(
        max_length=20,
        choices=NotificationRole.choices,
        default=NotificationRole.ALL,
    )

    priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.LOW,
    )

    message = models.CharField(max_length=255)
    route = models.CharField(max_length=255, blank=True, default="")

    is_active = models.BooleanField(default=True)

    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company.code} | {self.role} | {self.priority} | {self.message[:30]}"
