import datetime
import secrets
from django.contrib.auth.models import (
    AbstractUser,
    UserManager as DjangoUserManager,
)
from django.core.exceptions import ValidationError
from django.db import models
from config.validators import validate_profile_picture

# Manager
class UserManager(DjangoUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        return super().create_superuser(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )

# Course
class Course(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code_prefix = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    default_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.name} ({self.code_prefix})"
    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code_prefix = self.code_prefix.upper().strip()
        super().save(*args, **kwargs)

# User
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        GRADUATED = "GRADUATED", "Graduated"
        SUSPENDED = "SUSPENDED", "Suspended"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        INACTIVE = "INACTIVE", "Inactive"
    current_year = datetime.datetime.now().year
    ADMISSION_YEAR_CHOICES = [(y, y) for y in range(2020, current_year + 1)]
    email = models.EmailField()
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_industrial_training = models.BooleanField(default=False)
    is_profile_complete = models.BooleanField(default=False)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        help_text="Permanent login username.",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_users",
    )
    temporary_password = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    additional_phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=20,
        choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")],
        blank=True,
        null=True,
    )
    address = models.TextField(blank=True, null=True)
    state_of_origin = models.CharField(max_length=100, blank=True, null=True)
    profile_picture_url = models.URLField(
        blank=True,
        null=True,
        help_text="Cloudinary URL for profile picture. Max 2MB."
    )
    # Managers
    objects = UserManager()
    all_objects = models.Manager()
    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(is_deleted=False),
                name='unique_email_not_deleted'
            )
        ]

    def __str__(self):
        return f"[{self.role}] {self.username}"
    # Temporary password generation
    @staticmethod
    def generate_temporary_password(length=10):
        return secrets.token_urlsafe(length)[:length]
    # Username generation
    @staticmethod
    def generate_username():
        last_user = (
            User.all_objects.filter(username__startswith="STEPH")
            .order_by("username")
            .last()
        )
        if last_user:
            try:
                sequence = (
                    int(last_user.username.replace("STEPH", "")) + 1
                )
            except ValueError:
                sequence = 1
        else:
            sequence = 1
        return f"STEPH{sequence:06d}"
    def save(self, *args, **kwargs):
    # Ensure all Django superusers are ADMINs
        if self.is_superuser:
            self.role = self.Role.ADMIN

        if self.pk:
            old = User.all_objects.get(pk=self.pk)
            if (
                old.role == self.Role.STUDENT
                and old.username != self.username
            ):
                raise ValidationError(
                    "Student username cannot be modified."
                )

        if (
            self.role == self.Role.STUDENT
            and not self.pk
            and not self.username
        ):
            self.username = self.generate_username()

        super().save(*args, **kwargs)

# Student Course
class StudentCourse(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="students",
    )
    enrollment_id = models.CharField(max_length=30, unique=True)
    admission_year = models.PositiveIntegerField(
        choices=User.ADMISSION_YEAR_CHOICES,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    started_at = models.DateField(auto_now_add=True)
    completed_at = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course"
            )
        ]
    def __str__(self):
        return f"{self.student} - {self.course}"
    def save(self, *args, **kwargs):
        if not self.enrollment_id:
            self.enrollment_id = self.generate_enrollment_id()
        super().save(*args, **kwargs)
    def generate_enrollment_id(self):
        short_year = str(self.admission_year)[-2:]
        prefix = f"{self.course.code_prefix}/{short_year}/"
        last = (
            StudentCourse.objects.filter(
                course=self.course,
                admission_year=self.admission_year,
                enrollment_id__startswith=prefix,
            )
            .order_by("enrollment_id")
            .last()
        )
        if last:
            sequence = int(last.enrollment_id.split("/")[-1]) + 1
        else:
            sequence = 1
        return f"{prefix}{sequence:04d}"
