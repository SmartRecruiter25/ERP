from django.urls import path
from .views import AttendanceListView, AttendanceSummaryView , AttendanceEmployeesFilterView

urlpatterns = [
    path("logs/", AttendanceListView.as_view(), name="attendance-logs"),
    path("summary/", AttendanceSummaryView.as_view(), name="attendance-summary"),
    path("employees/", AttendanceEmployeesFilterView.as_view(), name="attendance-employees"),

]