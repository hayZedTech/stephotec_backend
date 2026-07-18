from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import Course, StudentCourse
from config.validators import (
    validate_document_file,
    validate_video_file,
    validate_learning_content_file,
    validate_assignment_submission_file,
)

User = get_user_model()


class LearningContent(models.Model):
    """Course learning materials and resources"""
    class ContentType(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        DOCUMENT = "DOCUMENT", "Document"
        ARTICLE = "ARTICLE", "Article"
        QUIZ = "QUIZ", "Quiz"
        RESOURCE = "RESOURCE", "Resource"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="learning_contents"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.DOCUMENT
    )
    file = models.FileField(
        upload_to="learning_content/",
        blank=True,
        null=True,
        validators=[validate_learning_content_file],
        help_text="Supports documents (PDF, Word, Excel, etc.) and videos. Max 50MB."
    )
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class Assignment(models.Model):
    """Course assignments and tasks"""
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CLOSED = "CLOSED", "Closed"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    instructions = models.TextField(blank=True)
    file = models.FileField(
        upload_to="assignments/",
        blank=True,
        null=True,
        validators=[validate_document_file],
        help_text="Assignment instruction files. Max 10MB. Supported: PDF, Word, Excel, PowerPoint."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    due_date = models.DateTimeField()
    max_score = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date"]

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class AssignmentSubmission(models.Model):
    """Student assignment submissions"""
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        GRADED = "GRADED", "Graded"
        LATE = "LATE", "Late"

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assignment_submissions"
    )
    file = models.FileField(
        upload_to="submissions/",
        validators=[validate_assignment_submission_file],
        help_text="Student submission files. Max 10MB. Supported: PDF, Word, Excel, ZIP."
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_submissions"
    )

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.assignment.title} - {self.student.username}"


class Attendance(models.Model):
    """Student attendance tracking"""
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        EXCUSED = "EXCUSED", "Excused"

    student_course = models.ForeignKey(
        StudentCourse,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_attendance"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student_course", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student_course.student.username} - {self.date}"


class Certificate(models.Model):
    """Student certificates and credentials"""
    class Status(models.TextChoices):
        EARNED = "EARNED", "Earned"
        ISSUED = "ISSUED", "Issued"
        REVOKED = "REVOKED", "Revoked"

    student_course = models.ForeignKey(
        StudentCourse,
        on_delete=models.CASCADE,
        related_name="certificates"
    )
    title = models.CharField(max_length=255)
    certificate_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EARNED
    )
    earned_date = models.DateField()
    issued_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to="certificates/", blank=True, null=True)
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_certificates"
    )

    class Meta:
        ordering = ["-earned_date"]

    def __str__(self):
        return f"{self.student_course.student.username} - {self.title}"


class Handout(models.Model):
    """Paid handouts/study materials for students"""
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="handouts"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="handouts/")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class HandoutPurchase(models.Model):
    """Track handout purchases and access"""
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    handout = models.ForeignKey(
        Handout,
        on_delete=models.CASCADE,
        related_name="purchases"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="handout_purchases"
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    transaction_id = models.CharField(max_length=255, unique=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("handout", "student")
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.student.username} - {self.handout.title}"


class Notification(models.Model):
    """System notifications for users"""
    class Type(models.TextChoices):
        ASSIGNMENT = "ASSIGNMENT", "Assignment"
        GRADE = "GRADE", "Grade"
        ATTENDANCE = "ATTENDANCE", "Attendance"
        CERTIFICATE = "CERTIFICATE", "Certificate"
        HANDOUT = "HANDOUT", "Handout"
        SYSTEM = "SYSTEM", "System"
        MESSAGE = "MESSAGE", "Message"

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM
    )
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"


class Message(models.Model):
    """Direct messaging between users"""
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_messages"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.subject}"


class StudentLearningContent(models.Model):
    """Track learning content assigned to students per course"""
    student_course = models.ForeignKey(
        StudentCourse,
        on_delete=models.CASCADE,
        related_name="assigned_learning_contents"
    )
    learning_content = models.ForeignKey(
        LearningContent,
        on_delete=models.CASCADE,
        related_name="assigned_to_students"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student_course", "learning_content")
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.student_course.student.username} - {self.learning_content.title}"


class StudentAssignment(models.Model):
    """Track assignments assigned to students"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_assignments"
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="assigned_to_students"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "assignment")
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"


class StudentCertificate(models.Model):
    """Track certificates assigned to students"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_certificates"
    )
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name="assigned_to_students"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "certificate")
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.student.username} - {self.certificate.title}"


class StudentHandout(models.Model):
    """Track handouts assigned to students"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_handouts"
    )
    handout = models.ForeignKey(
        Handout,
        on_delete=models.CASCADE,
        related_name="assigned_to_students"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "handout")
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.student.username} - {self.handout.title}"
