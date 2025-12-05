from django.urls import path
from .views import PendingLeaveRequestsView, LeaveRequestApproveRejectView

urlpatterns = [
    path("leave-requests/pending/", PendingLeaveRequestsView.as_view(), name="ess-leaves-pending"),
    path("leave-requests/<int:pk>/action/", LeaveRequestApproveRejectView.as_view(), name="ess-leave-action"),
]