from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Course, StudentCourse


class StudentCourseInline(admin.TabularInline):
    model = StudentCourse
    extra = 0
    readonly_fields = ("student_id",)
    autocomplete_fields = ("course",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = (
        "username",
        "email",
        "role",
        "status",
        "is_profile_complete",
        "created_at",
    )

    list_filter = (
        "role",
        "status",
        "is_profile_complete",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    readonly_fields = (
        "created_at",
        "last_login",
        "date_joined",
    )

    inlines = [StudentCourseInline]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "email", "bio")}),
        ("Student", {"fields": ("role", "status", "is_industrial_training", "is_profile_complete")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined", "created_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "role",
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "status",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.role == User.Role.STUDENT:
            readonly.extend(["username", "role"])
        return readonly


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code_prefix", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code_prefix")


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "student_id",
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
        "student_id",
    )
    autocomplete_fields = (
        "student",
        "course",
    )