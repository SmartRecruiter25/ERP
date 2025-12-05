from rest_framework import serializers


class SmartShiftSuggestionSerializer(serializers.Serializer):
    day = serializers.CharField()
    date = serializers.DateField()
    shift_name = serializers.CharField()
    shift_code = serializers.CharField()
    assigned_employees = serializers.ListField(
        child=serializers.CharField()
    )
    notes = serializers.CharField(allow_blank=True)

class WorkforceRecommendationSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    priority = serializers.CharField()  # high / medium / low


class WorkforcePlanningSerializer(serializers.Serializer):
    department_id = serializers.IntegerField(allow_null=True)
    department_name = serializers.CharField()
    period = serializers.CharField()          # this_month / next_quarter ...
    period_label = serializers.CharField()    # "This Month" / "Next Quarter"

    current_staff = serializers.IntegerField()
    required_staff = serializers.IntegerField()
    hiring_needed = serializers.IntegerField()
    skill_gap_index = serializers.FloatField()

    recommendations = WorkforceRecommendationSerializer(many=True)