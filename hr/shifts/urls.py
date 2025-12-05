from django.urls import path
from .views import ESSMyShiftsView

urlpatterns = [
    path("ess/", ESSMyShiftsView.as_view(), name="ess-shifts"),
]