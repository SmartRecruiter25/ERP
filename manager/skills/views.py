from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from manager.skills.serializers import (
    SkillProofSerializer,
    SkillsSummarySerializer,
    SkillsOverviewResponseSerializer ,
)

from hr.resume.models import SkillProof
from hr.job_requirements.models import JobRequirementSkill
from hr.org_structure.models import Company , Department
from hr.employees.models import Employee, EmployeeStatus
from hr.skills.models import EmployeeSkill
from accounts.permissions import IsAdminOrHR



class BaseCompanyMixin:
    def get_company(self, request):
        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is not None:
            return employee_profile.company
        return Company.objects.first()


class SkillsSummaryView(BaseCompanyMixin, APIView):

    permission_classes = [IsAuthenticated , IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            data = {
                "total_skill_proofs": 0,
                "unique_skills_count": 0,
                "top_existing_skills": [],
                "top_required_skills": [],
            }
            serializer = SkillsSummarySerializer(data)
            return Response(serializer.data)

        proofs_qs = SkillProof.objects.filter(employee__company=company)

        total_skill_proofs = proofs_qs.count()

        unique_skills_count = proofs_qs.values("skill_name").distinct().count()

        top_existing = (
            proofs_qs.values("skill_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        job_req_skills_qs = JobRequirementSkill.objects.filter(
            job_requirement__company=company
        )

        top_required = (
            job_req_skills_qs.values("skill_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        data = {
            "total_skill_proofs": total_skill_proofs,
            "unique_skills_count": unique_skills_count,
            "top_existing_skills": list(top_existing),
            "top_required_skills": list(top_required),
        }

        serializer = SkillsSummarySerializer(data)
        return Response(serializer.data)


class SkillProofListView(BaseCompanyMixin, APIView):

    permission_classes = [IsAuthenticated , IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            return Response([], status=200)

        qs = SkillProof.objects.filter(employee__company=company).select_related(
            "employee__user",
            "employee__department",
            "employee__job_title",
        )

        serializer = SkillProofSerializer(qs, many=True)
        return Response(serializer.data)


class SkillsOverviewView(BaseCompanyMixin, APIView):
    permission_classes = [IsAuthenticated , IsAdminOrHR]

    def get(self, request):
        company = self.get_company(request)
        if not company:
            empty = {"departments": [], "employees": []}
            serializer = SkillsOverviewResponseSerializer(empty)
            return Response(serializer.data)

        dept_qs = Department.objects.filter(company=company).order_by("name")
        departments_data = [
            {"id": None, "name": "All Departments"}
        ] + [
            {"id": d.id, "name": d.name} for d in dept_qs
        ]

        dept_id = request.query_params.get("department_id")
        employee_filters = {
            "company": company,
            "status": EmployeeStatus.ACTIVE,
        }
        if dept_id and dept_id.isdigit():
            employee_filters["department_id"] = int(dept_id)

        team_qs = (
            Employee.objects
            .filter(**employee_filters)
            .select_related("user", "job_title", "department")
            .prefetch_related(
                Prefetch(
                    "skills",
                    queryset=EmployeeSkill.objects.select_related("skill"),
                )
            )
        )

        employees_data = []
        for emp in team_qs:
            name = emp.user.get_full_name() or emp.user.username
            job_title = emp.job_title.title_name if emp.job_title else None
            department_name = emp.department.name if emp.department else None

            skills_list = []
            for es in emp.skills.all():
                skills_list.append(
                    {
                        "name": es.skill.name,
                        "level": es.level,
                        "proficiency": es.proficiency_percent,
                    }
                )

            employees_data.append(
                {
                    "id": emp.id,
                    "name": name,
                    "job_title": job_title,
                    "department": department_name,
                    "skills": skills_list,
                }
            )

        data = {
            "departments": departments_data,
            "employees": employees_data,
        }

        serializer = SkillsOverviewResponseSerializer(data)
        return Response(serializer.data)