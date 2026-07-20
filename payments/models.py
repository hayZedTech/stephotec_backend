from django.db import models
from accounts.models import StudentCourse
from django.contrib.auth import get_user_model

User = get_user_model()


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "PAID", "Paid"
        PARTIAL = "PARTIAL", "Partial"
        UNPAID = "UNPAID", "Unpaid"

    student_course = models.OneToOneField(
        StudentCourse,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    course_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    notes = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_updated"]

    def __str__(self):
        return f"{self.student_course} — {self.status}"

    @property
    def outstanding(self):
        return max(self.course_fee - self.amount_paid, 0)

    def save(self, *args, **kwargs):
        if self.amount_paid >= self.course_fee and self.course_fee > 0:
            self.status = self.Status.PAID
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.UNPAID
        super().save(*args, **kwargs)
