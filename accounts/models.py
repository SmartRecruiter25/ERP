from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("hr", "HR"),
        ("employee", "Employee"),
        ("manager", "Manager"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="employee")

    def __str__(self):
        return f"{self.username} ({self.role})"


class Profile(models.Model):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="profile")


    name = models.CharField(max_length=255 , blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)  
    bio = models.TextField(blank=True, null=True)                        
    image = models.ImageField(upload_to="profiles/", blank=True, null=True)

    department = models.CharField(max_length=255, blank=True, null=True)
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    manager = models.CharField(max_length=255, blank=True, null=True)    
    work_location = models.CharField(max_length=255, blank=True, null=True)
    dashboard_mode = models.CharField(
    max_length=20,
    choices=[
        ("smart", "Smart Dashboard"),
        ("separate", "Separate Dashboards"),
    ],
    default="smart",
)

    def __str__(self):
        return f"Profile of {self.user.username}"