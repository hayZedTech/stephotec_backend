from django.contrib import admin
from .models import User, Course, StudentCourse


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "role",
        "status",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "status",
        "is_superuser",
        "is_staff",
        "is_active",
        "is_industrial_training",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
    )

    readonly_fields = (
        "created_at",
        "last_login",
        "date_joined",
    )

    ordering = ("-date_joined",)


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
    autocomplete_fields = (
        "student",
        "course",
    )