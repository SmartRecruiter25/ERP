# admin_panel/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_actions",
        help_text="المستخدم الذي قام بالفعل (إن وجد).",
    )
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.actor.username if self.actor else "System"
        return f"{who}: {self.action} @ {self.created_at}"


class Role(models.Model):
    """
    جدول للأدوار الخاصة بالنظام (لإدارة شاشة Manage Roles)
    المفتاح key يطابق القيم الموجودة في User.role قدر الإمكان.
    """
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=20,
        blank=True,
        help_text="كود لون اختياري لعرض البادج في الواجهة (مثلاً #4CAF50).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.name or self.key


class SystemSetting(models.Model):
    """
    إعدادات عامة للنظام يمكن إدارتها من شاشة System Settings.
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key