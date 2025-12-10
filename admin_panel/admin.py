from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "created_at")
    list_filter = ("actor", "created_at")
    search_fields = ("action", "actor__username", "actor__email")