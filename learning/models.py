from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import Course, StudentCourse, StudentGroup
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
    file = models.URLField(
        blank=True,
        null=True,
        help_text="Cloudinary URL for uploaded file (document or video)."
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
    file = models.URLField(
        blank=True,
        null=True,
        help_text="Cloudinary URL for assignment file."
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
    file = models.URLField(
        help_text="Cloudinary URL for student submission file."
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

    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

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
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING
    )
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_attendance"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_attendance"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
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
    certificate_number = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EARNED
    )
    earned_date = models.DateField()
    issued_date = models.DateField(null=True, blank=True)
    file = models.URLField(blank=True, null=True, help_text="Cloudinary URL for certificate file.")
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

    def generate_certificate_number(self):
        import datetime
        short_year = str(datetime.datetime.now().year)[-2:]
        prefix = f"CERT/{short_year}/"
        existing_ids = Certificate.objects.filter(certificate_number__startswith=prefix).values_list("certificate_number", flat=True)
        max_seq = 0
        for cid in existing_ids:
            try:
                seq_part = int(cid.split("/")[-1])
                if seq_part > max_seq:
                    max_seq = seq_part
            except (ValueError, IndexError):
                pass
        next_seq = max_seq + 1
        candidate = f"{prefix}{next_seq:05d}"
        while Certificate.objects.filter(certificate_number=candidate).exists():
            next_seq += 1
            candidate = f"{prefix}{next_seq:05d}"
        return candidate

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        super().save(*args, **kwargs)


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
    file = models.URLField(help_text="Cloudinary URL for handout file.")
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


class Brochure(models.Model):
    """Course brochure / outline uploaded by admin for courses"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="brochures"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.URLField(help_text="Cloudinary URL for brochure / course outline file.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class Quiz(models.Model):
    """Interactive quiz or practice test for a course"""
    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner Level"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate Level"
        ADVANCED = "ADVANCED", "Advanced Level"
        GENERAL = "GENERAL", "General Practice"

    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_quizzes"
    )
    courses = models.ManyToManyField(
        Course,
        related_name="quizzes",
        blank=True,
        help_text="Courses that can access this quiz."
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER
    )
    duration_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Test duration limit in minutes."
    )
    passing_score_percentage = models.PositiveIntegerField(
        default=70,
        help_text="Minimum score percentage required to pass."
    )
    display_questions_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of questions to randomly select. Leave blank to display all."
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return f"{self.course.code_prefix} - {self.title}"


class QuizQuestion(models.Model):
    """Multiple choice question for a quiz"""
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    question_text = models.TextField()
    explanation = models.TextField(
        blank=True,
        help_text="Detailed explanation of the correct answer shown after completion."
    )
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}: {self.question_text[:50]}"


class QuestionOption(models.Model):
    """Answer choice for a quiz question"""
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="options"
    )
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.option_text} {'(Correct)' if self.is_correct else ''}"


class QuizAttempt(models.Model):
    """Student attempt record for a quiz"""
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    score_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    passed = models.BooleanField(default=False)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers_count = models.PositiveIntegerField(default=0)
    answers_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON payload storing student selected option IDs and question feedback."
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} ({self.score_percentage}%)"


class ClassMaterial(models.Model):
    """Daily class code, files, or folders sent directly to student groups or individual students"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.URLField(blank=True, null=True, help_text="Cloudinary URL for uploaded class file or code archive.")
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.CharField(max_length=50, blank=True)
    files = models.JSONField(
        default=list,
        blank=True,
        help_text="List of file objects: [{'url': '...', 'name': '...', 'size': '...'}]"
    )
    assigned_groups = models.ManyToManyField(
        StudentGroup,
        blank=True,
        related_name="class_materials"
    )
    assigned_students = models.ManyToManyField(
        User,
        blank=True,
        related_name="class_materials",
        limit_choices_to={"role": "STUDENT"}
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_class_materials"
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Class Material: {self.title}"


class LectureSchedule(models.Model):
    """Lecture timetable and class schedule for groups and students"""
    class Mode(models.TextChoices):
        ONLINE = "ONLINE", "Online (Virtual)"
        PHYSICAL = "PHYSICAL", "Physical (Classroom)"
        HYBRID = "HYBRID", "Hybrid"

    title = models.CharField(max_length=255)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecture_schedules"
    )
    assigned_groups = models.ManyToManyField(
        StudentGroup,
        blank=True,
        related_name="lecture_schedules"
    )
    assigned_students = models.ManyToManyField(
        User,
        blank=True,
        related_name="lecture_schedules",
        limit_choices_to={"role": "STUDENT"}
    )
    days_of_week = models.JSONField(
        default=list,
        help_text="List of days of week, e.g. ['MONDAY', 'WEDNESDAY', 'FRIDAY']"
    )
    day_times = models.JSONField(
        default=list,
        blank=True,
        help_text="List of per-day timings: [{'day': 'MONDAY', 'start_time': '10:30:00', 'end_time': '12:00:00', 'duration_minutes': 90}, ...]"
    )
    start_time = models.TimeField(help_text="Start time of the lecture (e.g. 10:30)")
    end_time = models.TimeField(help_text="End time of the lecture (e.g. 12:00)")
    duration_minutes = models.PositiveIntegerField(
        default=90,
        help_text="Class duration in minutes (e.g. 45, 60, 90, 120)"
    )
    mode = models.CharField(
        max_length=20,
        choices=Mode.choices,
        default=Mode.PHYSICAL
    )
    venue_or_link = models.CharField(
        max_length=500,
        blank=True,
        help_text="Meeting URL (Google Meet / Zoom) or physical classroom room/hall."
    )
    instructor_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of the instructor / tutor taking this lecture."
    )
    color_tag = models.CharField(
        max_length=30,
        default="#2563eb",
        help_text="Hex color code or theme for timetable card display."
    )
    notes = models.TextField(
        blank=True,
        help_text="Preparation notes, tools, or syllabus reference for students."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable or disable this lecture schedule."
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_lecture_schedules"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time", "created_at"]

    def __str__(self):
        days_str = ", ".join(self.days_of_week) if self.days_of_week else "Unscheduled"
        return f"{self.title} ({days_str} @ {self.start_time.strftime('%I:%M %p') if self.start_time else ''})"




