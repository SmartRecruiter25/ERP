# admin_panel/urls.py
from django.urls import path
from .views import (
    AdminDashboardSummaryView,

    DepartmentListCreateView,
    DepartmentDetailView,

    RoleListCreateView,
    RoleDetailView,

    SystemSettingListCreateView,
    SystemSettingDetailView,
)

urlpatterns = [

    path(
        "dashboard/summary/",
        AdminDashboardSummaryView.as_view(),
        name="admin_dashboard_summary",
    ),


    path(
        "departments/",
        DepartmentListCreateView.as_view(),
        name="admin_departments_list_create",
    ),
    path(
        "departments/<int:pk>/",
        DepartmentDetailView.as_view(),
        name="admin_departments_detail",
    ),

    path(
        "roles/",
        RoleListCreateView.as_view(),
        name="admin_roles_list_create",
    ),
    path(
        "roles/<int:pk>/",
        RoleDetailView.as_view(),
        name="admin_roles_detail",
    ),

 
    path(
        "settings/",
        SystemSettingListCreateView.as_view(),
        name="admin_settings_list_create",
    ),
    path(
        "settings/<int:pk>/",
        SystemSettingDetailView.as_view(),
        name="admin_settings_detail",
    ),
]