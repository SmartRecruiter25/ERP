from rest_framework import serializers
from hr.resume.models import SkillProof
from hr.job_requirements.models import JobRequirementSkill
from hr.skills.models import EmployeeSkill


class SkillProofSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    employee_name = serializers.SerializerMethodField()
    department = serializers.CharField(source="employee.department.name", read_only=True)
    job_title = serializers.CharField(source="employee.job_title.title_name", read_only=True)

    class Meta:
        model = SkillProof
        fields = [
            "id",
            "employee_code",
            "employee_name",
            "department",
            "job_title",
            "skill_name",
            "skill_level",
            "proof_type",
            "status",
            "created_at",
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class TopSkillSerializer(serializers.Serializer):
    skill_name = serializers.CharField()
    count = serializers.IntegerField()


class SkillsSummarySerializer(serializers.Serializer):
    total_skill_proofs = serializers.IntegerField()
    unique_skills_count = serializers.IntegerField()
    top_existing_skills = TopSkillSerializer(many=True)
    top_required_skills = TopSkillSerializer(many=True)

class EmployeeSkillItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    level = serializers.CharField()
    proficiency = serializers.IntegerField()


class SkillsOverviewEmployeeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    job_title = serializers.CharField(allow_null=True)
    department = serializers.CharField(allow_null=True)
    skills = EmployeeSkillItemSerializer(many=True)


class SkillsOverviewResponseSerializer(serializers.Serializer):
    departments = serializers.ListField(
        child=serializers.DictField()
    )
    employees = SkillsOverviewEmployeeSerializer(many=True)