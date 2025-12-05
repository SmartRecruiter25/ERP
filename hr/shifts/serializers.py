from rest_framework import serializers
from .models import Shift, ShiftAssignment


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["id", "name", "start_time", "end_time", "location", "color"]


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    shift = ShiftSerializer()

    class Meta:
        model = ShiftAssignment
        fields = ["id", "date", "shift", "notes"]