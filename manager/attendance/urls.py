from django.urls import path
from .views import (
    AttendanceListView,
    AttendanceSummaryView,
    AttendanceEmployeesFilterView,
    CheckInView,
    CheckOutView,
)

urlpatterns = [
    path("logs/", AttendanceListView.as_view(), name="attendance-logs"),
    path("summary/", AttendanceSummaryView.as_view(), name="attendance-summary"),
    path("employees/", AttendanceEmployeesFilterView.as_view(), name="attendance-employees"),

    path("check-in/", CheckInView.as_view(), name="attendance-check-in"),
    path("check-out/", CheckOutView.as_view(), name="attendance-check-out"),
]