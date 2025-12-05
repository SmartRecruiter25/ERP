from rest_framework import serializers
from hr.org_structure.models import Department
from .models import Role, SystemSetting


class DepartmentSerializer(serializers.ModelSerializer):
    employees_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = "__all__"

        def get_employees_count(self, obj):
        # نحاول نستخدم العلاقة العكسية الافتراضية للموظف
            rel = getattr(obj, "employee_set", None)
            if rel is not None and hasattr(rel, "count"):
                return rel.count()
            rel2 = getattr(obj, "employees", None)
            if rel2 is not None and hasattr(rel2, "count"):
                return rel2.count()
            return 0


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "key", "name", "description", "color", "is_active"]


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value", "description", "updated_at"]
        read_only_fields = ["id", "updated_at"]

