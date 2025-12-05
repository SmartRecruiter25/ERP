from django.urls import path
from .views import ContractsSummaryView, ContractsListView

urlpatterns = [
    path("summary/", ContractsSummaryView.as_view(), name="contracts-summary"),
    path("list/", ContractsListView.as_view(), name="contracts-list"),
]