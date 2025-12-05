from django.db import models
from hr.employees.models import Employee


class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SkillLevel(models.TextChoices):
    BEGINNER = "Beginner", "Beginner"
    INTERMEDIATE = "Intermediate", "Intermediate"
    ADVANCED = "Advanced", "Advanced"
    EXPERT = "Expert", "Expert"


class EmployeeSkill(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="employee_skills",
    )
    level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.BEGINNER,
    )
    proficiency_percent = models.PositiveIntegerField(
        default=0,
        help_text="0–100 لعرض الـ progress bar",
    )

    class Meta:
        unique_together = (("employee", "skill"),)
        ordering = ["employee__employee_code", "skill__name"]

    def __str__(self):
        return f"{self.employee} - {self.skill} ({self.level}, {self.proficiency_percent}%)"