
from django.urls import path
from manager.ai.views import (SmartShiftsView , WorkforcePlanningView ,  ResumeReceiveAI,
    ResumeMatchAI,
    AttendanceEventAI , )

urlpatterns = [
    path("smart-shifts/", SmartShiftsView.as_view(), name="smart-shifts"),
    path( "workforce-planning/", WorkforcePlanningView.as_view(), name="workforce-planning"),
    path("resume/receive/", ResumeReceiveAI.as_view(), name="ai-resume-receive"),
    path("resume/match/", ResumeMatchAI.as_view(), name="ai-resume-match"),
    path("attendance/event/", AttendanceEventAI.as_view(), name="ai-attendance-event"),
   

]