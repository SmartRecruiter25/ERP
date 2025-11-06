# accounts/views.py
from rest_framework import generics, permissions, status , parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model , update_session_auth_hash
from .serializers import (
    RegisterSerializer,
     UserSerializer,
      CustomTokenObtainPairSerializer ,
      ProfileSerializer, 
      UserSerializer , 
      ChangePasswordSerializer ,
      UpdateUserSerializer ,
      AdminChangeUserRoleSerializer ,
)
from .models import Profile , User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from . permissions import IsHR , IsManager , IsAdmin , IsEmployee ,  IsHRorAdmin, IsManagerOrAdmin , IsOwnerOrAdmin

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        self.check_object_permissions(request, profile)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        base = super().get_permissions()
        # أضيفي صلاحية كائنية لهذه الـ view
        self.permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        return [perm for perm in base]

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class UpdateUserView(generics.UpdateAPIView):
    serializer_class = UpdateUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    # نسمح بـ PUT و PATCH، الافتراضي في UpdateAPIView يدعمهم
    http_method_names = ["put", "patch", "options", "head"]

    def get_object(self):
        # نعيد المستخدم الحالي فقط
        return self.request.user

    def get_serializer_context(self):
        # حتى نستخدم request داخل الـ serializer (للتحقق من الإيميل/اليوزرنيم)
        ctx = super().get_serializer_context()
        ctx.update({"request": self.request})
        return ctx

class EmployeeListView(generics.ListAPIView):
    queryset = User.objects.filter(role="employee")
    serializer_class = UserSerializer
    permission_classes = [IsHR]

class ManagerDashboardView(APIView):
    permission_classes = [IsManager | IsAdmin]

    def get(self, request):
        return Response({"message": "Welcome Manager/Admin!"})

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save()

        # خيار 1: إبقاء المستخدم مسجّل الدخول (Session-based). مع JWT غالبًا غير ضروري.
        # update_session_auth_hash(request, user)

        # خيار 2 (مستحسن مع JWT): اطلب من الفرونت حذف التوكنات والـ re-login
        return Response({"detail": "Password changed successfully. Please log in again."}, status=status.HTTP_200_OK)

class AdminChangeUserRoleView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminChangeUserRoleSerializer
    permission_classes = [IsAdmin]
    lookup_field = "id"   # تعديل حسب المفتاح الذي ستستخدمينه في URL