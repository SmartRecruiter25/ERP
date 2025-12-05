from django.contrib import admin
from django.urls import path , include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

def home(request):
    return HttpResponse("✅ ERP backend is running!")

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/ess/", include("hr.ess.urls")),
    path("api/shifts/", include("hr.shifts.urls")),
    path("api/manager/dashboard/", include("manager.dashboard.urls")),
    path("api/manager/people/", include("manager.people.urls")),
    path("api/manager/ess/", include("manager.ess.urls")), 
    path("api/manager/ai/", include("manager.ai.urls")),
    path("api/manager/contracts/", include("manager.contracts.urls")),
    path("api/manager/attendance/", include("manager.attendance.urls")),
    path("api/manager/payroll/", include("manager.payroll.urls")),
    path("api/manager/skills/", include("manager.skills.urls")),
    path("api/admin/", include("admin_panel.urls")),

    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)