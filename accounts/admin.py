from django.contrib import admin
from .models import User, Course, StudentCourse, StudentUser, StaffUser


@admin.register(StudentUser)
class StudentUserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "status",
        "is_industrial_training",
        "is_profile_complete",
        "date_joined",
    )

    list_filter = (
        "status",
        "is_industrial_training",
        "is_profile_complete",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
    )

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Information", {"fields": ("first_name", "last_name", "email", "phone", "bio")}),
        ("Student Status", {"fields": ("status", "is_industrial_training", "is_profile_complete")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined", "created_at")}),
    )

    readonly_fields = (
        "created_at",
        "last_login",
        "date_joined",
    )

    ordering = ("-date_joined",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.STUDENT)


@admin.register(StaffUser)
class StaffUserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "job_title",
        "email",
        "status",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "job_title",
        "status",
        "is_superuser",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "job_title",
        "phone",
    )

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Information", {"fields": ("first_name", "last_name", "email", "phone")}),
        ("Staff Designation & Role", {"fields": ("job_title", "role", "status")}),
        ("Permissions & Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined", "created_at")}),
    )

    readonly_fields = (
        "created_at",
        "last_login",
        "date_joined",
    )

    ordering = ("-date_joined",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.ADMIN)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code_prefix", "default_fee", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code_prefix")


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "enrollment_id",
        "status",
        "admission_year",
        "is_primary",
    )
    list_filter = (
        "course",
        "status",
        "is_primary",
        "admission_year",
    )
    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__email",
        "student__username",
        "enrollment_id",
    )
    raw_id_fields = ("student",)
    autocomplete_fields = ("course",)