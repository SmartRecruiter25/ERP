from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from hr.ess.models import LeaveRequest, LeaveStatus
from manager.ess.serializers import LeaveRequestSerializer, LeaveApproveRejectSerializer


class PendingLeaveRequestsView(APIView):
 
    permission_classes = [IsAuthenticated]

    def get(self, request):

        qs = LeaveRequest.objects.filter(status=LeaveStatus.PENDING).select_related(
            "employee__user", "employee__department"
        )

        serializer = LeaveRequestSerializer(qs, many=True)
        return Response(serializer.data)


class LeaveRequestApproveRejectView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            leave_request = LeaveRequest.objects.select_related("employee").get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        if leave_request.status != LeaveStatus.PENDING:
            return Response(
                {"detail": "Only pending leave requests can be approved or rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        approver = getattr(request.user, "employee", None)  

        if action == "approve":
            leave_request.status = LeaveStatus.APPROVED
            leave_request.approver = approver
            leave_request.approved_at = timezone.now()
            leave_request.save()
        else: 
            leave_request.status = LeaveStatus.REJECTED
            leave_request.approver = approver
            leave_request.approved_at = timezone.now()
            if reason:
                leave_request.cancellation_reason = reason
            leave_request.save()

        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_200_OK)