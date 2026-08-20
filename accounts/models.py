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
    class DurationUnit(models.TextChoices):
        MONTHS = "MONTHS", "Months"
        WEEKS = "WEEKS", "Weeks"

    name = models.CharField(max_length=255, unique=True)
    code_prefix = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    default_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    duration_value = models.PositiveIntegerField(null=True, blank=True, default=0)
    duration_unit = models.CharField(
        max_length=10,
        choices=DurationUnit.choices,
        default=DurationUnit.MONTHS,
    )
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
    ADMISSION_YEAR_CHOICES = [(y, y) for y in range(2010, current_year + 1)]
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
    enrollment_date = models.DateField(blank=True, null=True, help_text="Optional Date Joined for course duration tracking.")
    gender = models.CharField(
        max_length=20,
        choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")],
        blank=True,
        null=True,
    )
    address = models.TextField(blank=True, null=True)
    state_of_origin = models.CharField(max_length=100, blank=True, null=True)
    STAFF_TITLE_CHOICES = [
        ("CEO & Founder", "CEO & Founder"),
        ("Chief Executive Officer (CEO)", "Chief Executive Officer (CEO)"),
        ("Managing Director", "Managing Director"),
        ("Academic Director", "Academic Director"),
        ("School Registrar", "School Registrar"),
        ("Senior Lecturer & Instructor", "Senior Lecturer & Instructor"),
        ("Academic Staff / Facilitator", "Academic Staff / Facilitator"),
        ("IT Director & Systems Manager", "IT Director & Systems Manager"),
        ("Bursar / Lead Accountant", "Bursar / Lead Accountant"),
        ("Administrative Officer", "Administrative Officer"),
        ("System Administrator", "System Administrator"),
    ]
    job_title = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        choices=STAFF_TITLE_CHOICES,
        default=None,
        help_text="Official staff role/designation displayed on Staff ID card and verification portal.",
    )
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
                fields=['email', 'role'],
                condition=models.Q(is_deleted=False),
                name='unique_email_role_not_deleted'
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
        existing_usernames = User.all_objects.filter(username__startswith="STEPH").values_list("username", flat=True)
        max_seq = 0
        for uname in existing_usernames:
            try:
                seq = int(uname.replace("STEPH", ""))
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                pass
        
        next_seq = max_seq + 1
        candidate = f"STEPH{next_seq:06d}"
        while User.all_objects.filter(username=candidate).exists():
            next_seq += 1
            candidate = f"STEPH{next_seq:06d}"
        return candidate
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

        # Auto-hash plain-text password if created/edited via Django admin
        # Skip if: empty, already hashed, or Django's unusable password marker ('!')
        if (
            self.password
            and not self.password.startswith(('pbkdf2_sha256$', 'pbkdf2_sha512$', 'argon2$', 'bcrypt$', 'sha1$', 'md5$', 'crypt$', '!'))
        ):
            self.set_password(self.password)

        # Sync Django's is_active with our custom status field
        # so users created via Django admin can log in without manual toggling
        if self.status in (self.Status.ACTIVE, self.Status.GRADUATED):
            self.is_active = True
        elif self.status in (self.Status.SUSPENDED, self.Status.WITHDRAWN, self.Status.INACTIVE):
            self.is_active = False

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
        
        existing_ids = StudentCourse.objects.filter(
            enrollment_id__startswith=prefix
        ).values_list("enrollment_id", flat=True)
        
        max_seq = 0
        for eid in existing_ids:
            try:
                seq_part = int(eid.split("/")[-1])
                if seq_part > max_seq:
                    max_seq = seq_part
            except (ValueError, IndexError):
                pass
        
        next_seq = max_seq + 1
        candidate = f"{prefix}{next_seq:04d}"
        
        while StudentCourse.objects.filter(enrollment_id=candidate).exists():
            next_seq += 1
            candidate = f"{prefix}{next_seq:04d}"
            
        return candidate



# Student Group
class StudentGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        related_name="student_groups_single",
        null=True,
        blank=True,
    )
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name="student_groups",
    )
    members = models.ManyToManyField(
        User,
        blank=True,
        related_name="student_groups",
        limit_choices_to={"role": "STUDENT"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.courses.exists():
            return f"{self.name} ({', '.join(c.name for c in self.courses.all())})"
        if self.course:
            return f"{self.name} ({self.course.name})"
        return self.name


# Proxy Models for Separate Django Admin Tables
class StudentUser(User):
    class Meta:
        proxy = True
        verbose_name = "Student"
        verbose_name_plural = "Students"


class StaffUser(User):
    class Meta:
        proxy = True
        verbose_name = "Staff / Administrator"
        verbose_name_plural = "Staff & Administrators"

