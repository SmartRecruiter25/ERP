from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Profile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
 
    model = User
    list_display = ("username", "email", "role", "is_staff", "is_active", "is_superuser")
    list_filter = ("role", "is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Role & permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "role",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                ),
            },
        ),
    )

    search_fields = ("username", "email")
    ordering = ("username",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "phone",
        "location",
        "department",
        "employee_id",
        "manager",
        "work_location",
        "dashboard_mode",
    )

    search_fields = (
        "user__username",
        "user__email",
        "name",
        "phone",
        "employee_id",
    )

    list_filter = ("department", "work_location", "dashboard_mode")