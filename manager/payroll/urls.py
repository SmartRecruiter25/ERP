from django.urls import path
from .views import PayrollSummaryView, PayrollRunListView

urlpatterns = [
    path("summary/", PayrollSummaryView.as_view(), name="payroll-summary"),
    path("runs/", PayrollRunListView.as_view(), name="payroll-runs"),
]