from rest_framework import serializers
from hr.ess.models import LeaveRequest
from .models import Announcement
from hr.employees.models import EmployeeDocument
from hr.payroll.models import Payslip
import calendar


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "leave_type",  
            "start_date",
            "end_date",
            "status",
            "reason",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    uploaded_date = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = [
            "id",
            "title",       
            "doc_type",     
            "file",        
            "uploaded_date"
        ]

    def get_uploaded_date(self, obj):
        dt = getattr(obj, "uploaded_at", None) or getattr(obj, "created_at", None)
        return dt.date() if dt else None

class ESSPayslipSerializer(serializers.ModelSerializer):
    month_label = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            "id",
            "year",
            "month",
            "month_label",
            "net_amount",
            "currency",
            "status",
            "file",
            "created_at",
        ]

    def get_month_label(self, obj):
 
        return f"{calendar.month_abbr[obj.month]} {obj.year}"


class AnnouncementSerializer(serializers.ModelSerializer):
    relative_date = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "body",
            "category",
            "created_at",
            "relative_date",
        ]

    def get_relative_date(self, obj):
        
        from django.utils import timezone

        today = timezone.now().date()
        days = (today - obj.created_at.date()).days

        if days <= 0:
            return "Today"
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"