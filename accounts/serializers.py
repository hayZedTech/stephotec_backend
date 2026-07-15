from rest_framework import serializers, exceptions
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Course, StudentCourse
from config.validators import validate_profile_picture

User = get_user_model()

class CourseSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(
        source="students.count",
        read_only=True,
    )
    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "code_prefix",
            "is_active",
            "student_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student_count",
            "created_at",
        ]

class StudentCourseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        write_only=True,
        source="course",
        required=True,
    )
    class Meta:
        model = StudentCourse
        fields = [
            "id",
            "course",
            "course_id",
            "enrollment_id",
            "admission_year",
            "status",
            "is_primary",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "enrollment_id",
            "started_at",
            "course",
        ]
        extra_kwargs = {
            "admission_year": {"required": False},
            "status": {"required": False, "default": "ACTIVE"},
            "is_primary": {"required": False, "default": False},
        }


class AdminStudentCreationSerializer(serializers.Serializer):
    # User fields
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    temporary_password = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    is_industrial_training = serializers.BooleanField(default=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    admission_year = serializers.IntegerField(read_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    additional_phone = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")], required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    state_of_origin = serializers.CharField(required=False, allow_blank=True)
    # StudentCourse fields
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(is_active=True),
        write_only=True,
        required=True,
    )
    admission_year_write = serializers.ChoiceField(
        choices=User.ADMISSION_YEAR_CHOICES,
        required=True,
        write_only=True,
        source="admission_year",
    )
    is_primary = serializers.BooleanField(default=True, write_only=True)
    # Read-only course info
    courses = StudentCourseSerializer(many=True, read_only=True)
    status = serializers.ChoiceField(
        choices=User.Status.choices,
        default=User.Status.ACTIVE,
        required=False,
    )
    profile_picture_url = serializers.URLField(required=False, allow_blank=True)

    def validate_email(self, value):
        existing = User.objects.filter(email__iexact=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                "A user account with this email already exists."
            )
        return value
    
    def create(self, validated_data):
        course = validated_data.pop("course_id")
        admission_year = validated_data.pop("admission_year")
        is_primary = validated_data.pop("is_primary", True)
        
        # Generate password based on course code
        temporary_password = f"Welcome@Stephotec{course.code_prefix}"
        
        user = User(
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            role=User.Role.STUDENT,
            status=validated_data.get("status", User.Status.ACTIVE),
            is_industrial_training=validated_data.get("is_industrial_training", False),
            bio=validated_data.get("bio", ""),
            phone=validated_data.get("phone", ""),
            additional_phone=validated_data.get("additional_phone", ""),
            date_of_birth=validated_data.get("date_of_birth"),
            gender=validated_data.get("gender", ""),
            address=validated_data.get("address", ""),
            state_of_origin=validated_data.get("state_of_origin", ""),
            temporary_password=temporary_password,
        )
        user.set_password(temporary_password)
        user.save()
        # Create StudentCourse record
        StudentCourse.objects.create(
            student=user,
            course=course,
            admission_year=admission_year,
            is_primary=is_primary,
        )
        return user
    
    def update(self, instance, validated_data):
        course = validated_data.pop("course_id", None)
        admission_year = validated_data.pop("admission_year", None)
        is_primary = validated_data.pop("is_primary", None)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.status = validated_data.get("status", instance.status)
        instance.is_industrial_training = validated_data.get(
            "is_industrial_training",
            instance.is_industrial_training,
        )
        instance.bio = validated_data.get("bio", instance.bio)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.additional_phone = validated_data.get("additional_phone", instance.additional_phone)
        instance.date_of_birth = validated_data.get("date_of_birth", instance.date_of_birth)
        instance.gender = validated_data.get("gender", instance.gender)
        instance.address = validated_data.get("address", instance.address)
        instance.state_of_origin = validated_data.get("state_of_origin", instance.state_of_origin)
        instance.save()
        # If course_id provided, add new StudentCourse or update existing
        if course and admission_year:
            StudentCourse.objects.update_or_create(
                student=instance,
                course=course,
                admission_year=admission_year,
                defaults={"is_primary": is_primary or False},
            )
        return instance

    def to_representation(self, instance):
        primary_course = instance.courses.filter(is_primary=True).first()
        admission_year = primary_course.admission_year if primary_course else None
        
        # Map gender values for display
        gender_display = instance.gender
        if instance.gender == "MALE":
            gender_display = "Male"
        elif instance.gender == "FEMALE":
            gender_display = "Female"
        elif instance.gender == "OTHER":
            gender_display = "Other"
        
        data = {
            "id": instance.id,
            "username": instance.username,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "email": instance.email,
            "role": instance.role,
            "status": instance.status,
            "is_industrial_training": instance.is_industrial_training,
            "bio": instance.bio,
            "phone": instance.phone,
            "additional_phone": instance.additional_phone,
            "date_of_birth": instance.date_of_birth,
            "gender": gender_display,
            "address": instance.address,
            "state_of_origin": instance.state_of_origin,
            "admission_year": admission_year,
            "profile_picture_url": instance.profile_picture_url,
            "temporary_password": instance.temporary_password,
            "courses": StudentCourseSerializer(
                instance.courses.all(),
                many=True
            ).data
        }
        return data

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_or_email = attrs.get("username", "").strip()
        password = attrs.get("password")
        if "@" in username_or_email:
            try:
                user_found = User.objects.get(email__iexact=username_or_email)
                username_to_auth = user_found.username
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed(
                    "No active account found with the given credentials"
                )
        else:
            username_to_auth = username_or_email
        attrs["username"] = username_to_auth
        authenticated_user = authenticate(
            username=username_to_auth,
            password=password
        )
        if not authenticated_user:
            raise exceptions.AuthenticationFailed(
                "No active account found with the given credentials"
            )
        if not authenticated_user.is_active:
            raise exceptions.AuthenticationFailed(
                "This account has been deactivated."
            )
        self.user = authenticated_user
        data = super().validate(attrs)
        data["user_id"] = self.user.id
        data["username"] = self.user.username
        data["email"] = self.user.email
        data["role"] = self.user.role
        data["status"] = self.user.status
        data["is_profile_complete"] = self.user.is_profile_complete
        data["is_industrial_training"] = self.user.is_industrial_training
        data["first_name"] = self.user.first_name
        data["last_name"] = self.user.last_name
        data["phone"] = self.user.phone
        data["additional_phone"] = self.user.additional_phone
        data["date_of_birth"] = self.user.date_of_birth
        # Map gender values for display
        gender_display = self.user.gender
        if self.user.gender == "MALE":
            gender_display = "Male"
        elif self.user.gender == "FEMALE":
            gender_display = "Female"
        elif self.user.gender == "OTHER":
            gender_display = "Other"
        data["gender"] = gender_display
        data["address"] = self.user.address
        data["state_of_origin"] = self.user.state_of_origin
        data["bio"] = self.user.bio
        data["profile_picture_url"] = self.user.profile_picture_url
        data["courses"] = StudentCourseSerializer(
            self.user.courses.all(),
            many=True
        ).data
        return data


class StudentProfileActivationSerializer(serializers.ModelSerializer):
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    phone = serializers.CharField(required=True, max_length=20)
    date_of_birth = serializers.DateField(required=True)
    gender = serializers.ChoiceField(choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")], required=True)
    address = serializers.CharField(required=True)
    state_of_origin = serializers.CharField(required=True)
    profile_picture_url = serializers.URLField(required=False, allow_blank=True)
    class Meta:
        model = User
        fields = ["new_password", "phone", "date_of_birth", "gender", "address", "profile_picture_url", "is_profile_complete"]
        read_only_fields = ["is_profile_complete"]
    def update(self, instance, validated_data):
        instance.phone = validated_data.get("phone", instance.phone)
        instance.date_of_birth = validated_data.get("date_of_birth", instance.date_of_birth)
        instance.gender = validated_data.get("gender", instance.gender)
        instance.address = validated_data.get("address", instance.address)
        instance.state_of_origin = validated_data.get("state_of_origin", instance.state_of_origin)
        instance.profile_picture_url = validated_data.get("profile_picture_url", instance.profile_picture_url)
        instance.is_profile_complete = True
        instance.temporary_password = None
        instance.set_password(validated_data["new_password"])
        instance.save()
        return instance


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["bio", "additional_phone", "address", "state_of_origin", "profile_picture_url"]
    
    def update(self, instance, validated_data):
        instance.bio = validated_data.get("bio", instance.bio)
        instance.additional_phone = validated_data.get("additional_phone", instance.additional_phone)
        instance.address = validated_data.get("address", instance.address)
        instance.state_of_origin = validated_data.get("state_of_origin", instance.state_of_origin)
        if "profile_picture_url" in validated_data and validated_data["profile_picture_url"]:
            instance.profile_picture_url = validated_data["profile_picture_url"]
        instance.save()
        return instance


class StudentProfileDetailSerializer(serializers.ModelSerializer):
    courses = StudentCourseSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "additional_phone",
            "date_of_birth",
            "gender",
            "address",
            "state_of_origin",
            "bio",
            "profile_picture_url",
            "status",
            "is_profile_complete",
            "courses",
        ]
        read_only_fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "status",
            "is_profile_complete",
            "courses",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        gender_display = instance.gender
        if instance.gender == "MALE":
            gender_display = "Male"
        elif instance.gender == "FEMALE":
            gender_display = "Female"
        elif instance.gender == "OTHER":
            gender_display = "Other"
        data["gender"] = gender_display
        return data


class StudentProfilePageSerializer(serializers.ModelSerializer):
    """Complete profile data for profile page display"""
    courses = StudentCourseSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "additional_phone",
            "date_of_birth",
            "gender",
            "address",
            "state_of_origin",
            "bio",
            "profile_picture_url",
            "status",
            "is_profile_complete",
            "is_industrial_training",
            "courses",
        ]
        read_only_fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "status",
            "is_profile_complete",
            "is_industrial_training",
            "courses",
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        gender_display = instance.gender
        if instance.gender == "MALE":
            gender_display = "Male"
        elif instance.gender == "FEMALE":
            gender_display = "Female"
        elif instance.gender == "OTHER":
            gender_display = "Other"
        data["gender"] = gender_display
        return data
