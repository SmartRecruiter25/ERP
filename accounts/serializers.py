# accounts/serializers.py

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from hr.employees.models import Employee
from hr.org_structure.models import Department
from .models import Profile
from django.db.models import Q

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "confirm_password",
            "role",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


class UpdateUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role"]

    def validate_email(self, value):
        user = self.context["request"].user
        if value and User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_username(self, value):
        user = self.context["request"].user
        if value and User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "name",
            "phone",
            "location",
            "bio",
            "department",
            "employee_id",
            "manager",
            "work_location",
            "image",
            "dashboard_mode",
        ]
        extra_kwargs = {"image": {"required": False}}


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        identifier = attrs.get(self.username_field) 

        if identifier:
            try:
                user = User.objects.get(
                    Q(username__iexact=identifier) | Q(email__iexact=identifier)
                )
            except User.DoesNotExist:
                raise AuthenticationFailed(
                    detail={
                        "detail": "Invalid username or password",
                        "code": "invalid_credentials",
                    }
                )

            attrs[self.username_field] = user.username

        try:
            data = super().validate(attrs)
        except AuthenticationFailed as exc:
            raise AuthenticationFailed(
                detail={
                    "detail": "Invalid username/email or password",
                    "code": "invalid_credentials",
                }
            ) from exc

        user_data = UserSerializer(self.user).data
        data["user"] = user_data
        return data

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        old_password = attrs.get("old_password")
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")

        if not user.check_password(old_password):
            raise serializers.ValidationError(
                {"old_password": "Old password is incorrect."}
            )

        if new_password != confirm_new_password:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."}
            )

        validate_password(new_password, user=user)

        return attrs


class AdminChangeUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role"]

class EmployeeOnboardingSerializer(serializers.Serializer):

    department_id = serializers.IntegerField()
    employee_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        if hasattr(user, "employee_profile"):
            raise serializers.ValidationError("Employee profile already exists for this user.")

        try:
            department = Department.objects.get(id=attrs["department_id"])
        except Department.DoesNotExist:
            raise serializers.ValidationError({"department_id": "Department not found."})

        attrs["department"] = department
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        department = validated_data["department"]
        employee_code = validated_data.get("employee_code") or ""
        company = getattr(department, "company", None)

        employee = Employee.objects.create(
            user=user,
            company=company,
            department=department,
            employee_code=employee_code,
        )
        return employee

class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "role", "status"]

    def get_full_name(self, obj):
        if hasattr(obj, "profile") and obj.profile.name:
            return obj.profile.name

        name = (obj.get_full_name() or "").strip()
        if name:
            return name

        return obj.username

    def get_status(self, obj):

        return "Active" if obj.is_active else "Inactive"