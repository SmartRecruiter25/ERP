from django.urls import path
from .views import  ( DashboardSummaryView ,
                      MyTeamDashboardView , 
                      HRMainDashboardView ,
                      UnifiedDashboardView , 
)

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="hr-dashboard-summary"),
    path("my-team/", MyTeamDashboardView.as_view(), name="manager-my-team-dashboard"),
    path("hr-main/", HRMainDashboardView.as_view(), name="manager-hr-main-dashboard"),
    path("", UnifiedDashboardView.as_view(), name="dashboard-unified"),



]