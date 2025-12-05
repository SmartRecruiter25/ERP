from django.urls import path
from .views import PeopleHubSummaryView, EmployeeListView, EmployeeCreateView

urlpatterns = [
    path("summary/", PeopleHubSummaryView.as_view(), name="people-summary"),
    path("employees/", EmployeeListView.as_view(), name="people-employees"),
    path("employees/create/", EmployeeCreateView.as_view(), name="people-employees-create"),

]