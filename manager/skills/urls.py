from django.urls import path
from .views import SkillsSummaryView, SkillProofListView , SkillsOverviewView

urlpatterns = [
    path("summary/", SkillsSummaryView.as_view(), name="skills-summary"),
    path("proofs/", SkillProofListView.as_view(), name="skills-proofs"),
    path("overview/", SkillsOverviewView.as_view(), name="skills-overview"),

]