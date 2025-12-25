from django.urls import path
from .views import ( PayrollSummaryView, 
PayrollRunListView , 
PayrollRunCreateView ,
PayrollRunGenerateItemsView , 
)

urlpatterns = [
    path("summary/", PayrollSummaryView.as_view(), name="payroll-summary"),
    path("runs/", PayrollRunListView.as_view(), name="payroll-runs"),
    path("runs/run/", PayrollRunCreateView.as_view(), name="payroll-run-create"), 
    path("runs/<int:pk>/generate-items/", PayrollRunGenerateItemsView.as_view(), name="payroll-run-generate-items"), 

]