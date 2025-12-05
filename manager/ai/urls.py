
from django.urls import path
from manager.ai.views import SmartShiftsView , WorkforcePlanningView

urlpatterns = [
    path("smart-shifts/", SmartShiftsView.as_view(), name="smart-shifts"),
     path( "workforce-planning/", WorkforcePlanningView.as_view(), name="workforce-planning"),
]