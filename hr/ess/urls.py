from django.urls import path
from .views import ( ESSDashboardSummaryView , 
                        ESSAttendanceView , 
                        ESSLeaveRequestsView, 
                        ESSLeaveRequestCreateView, 
                        ESSContractDocumentsView,
                        ESSDocumentListCreateView,
                        ESSPayslipListView ,
                        ESSAnnouncementsListView ,
)


urlpatterns = [
    path("summary/", ESSDashboardSummaryView.as_view(), name="ess-dashboard-summary"),
    path("attendance/", ESSAttendanceView.as_view(), name="ess-attendance"),


    path("leaves/", ESSLeaveRequestsView.as_view(), name="ess-leaves-list"),
    path("leaves/new/", ESSLeaveRequestCreateView.as_view(), name="ess-leaves-create"),


    path("contract-documents/", ESSContractDocumentsView.as_view(),name="ess-contract-documents"),

    path("documents/",ESSDocumentListCreateView.as_view(),name="ess-documents"),

    path("payslips/", ESSPayslipListView.as_view(), name="ess-payslips"),

    path("announcements/", ESSAnnouncementsListView.as_view(), name="ess_announcements"),


]