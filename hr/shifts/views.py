from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta
from calendar import monthrange

from hr.employees.models import Employee


def get_employee_for_user(user):
    from django.shortcuts import get_object_or_404
    return get_object_or_404(Employee, user=user)


def get_period_range(period):
    today = timezone.now().date()

    if period == "month":
        start = today.replace(day=1)
        end = today.replace(day=monthrange(today.year, today.month)[1])
    else:
        start = today - timedelta(days=today.weekday()) 
        end = start + timedelta(days=6)

    return start, end


class ESSMyShiftsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employee = get_employee_for_user(request.user)

        period = request.query_params.get("period", "week")
        start_date, end_date = get_period_range(period)

        qs = (
            ShiftAssignment.objects
            .select_related("shift")
            .filter(employee=employee, date__range=(start_date, end_date))
            .order_by("date", "shift__start_time")
        )

        def fmt(obj):
            return {
                "id": obj.id,
                "date": obj.date,
                "weekday": obj.date.strftime("%a"),
                "name": obj.shift.name,
                "start_time": obj.shift.start_time,
                "end_time": obj.shift.end_time,
                "location": obj.shift.location,
                "color": obj.shift.color,
            }

        shifts = [fmt(o) for o in qs]

        # Next Shift
        today = timezone.now().date()
        next_shift_obj = (
            ShiftAssignment.objects
            .select_related("shift")
            .filter(employee=employee, date__gte=today)
            .order_by("date", "shift__start_time")
            .first()
        )

        next_shift = fmt(next_shift_obj) if next_shift_obj else None

        return Response({
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "shifts": shifts,
            "next_shift": next_shift,
        })