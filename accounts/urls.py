from django.urls import path
from .views import ( RegisterView, 
        MeView ,
        LogoutView,
        CustomTokenObtainPairView ,
        ProfileView,
        UserListView,
        EmployeeListView, 
        ManagerDashboardView , ChangePasswordView ,
        UpdateUserView , 
        AdminChangeUserRoleView
)

from rest_framework_simplejwt.views import (
    TokenRefreshView, 
    TokenVerifyView
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("me/", MeView.as_view(), name="me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("users/", UserListView.as_view(), name="users"),
    path("employees/", EmployeeListView.as_view(), name="employee_list"),
    path("manager-dashboard/", ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("update-user/", UpdateUserView.as_view(), name="update_user"),
    path("admin/users/<int:id>/change-role/", AdminChangeUserRoleView.as_view(), name="admin_change_role"),



]
