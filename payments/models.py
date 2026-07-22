from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
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


class PaymentEntry(models.Model):
    """Individual payment transaction log for a Payment record."""

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Bank Transfer, Cash, POS",
    )
    note = models.TextField(
        blank=True,
        help_text="Additional details about this payment",
    )
    recorded_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_entries",
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.payment} — {self.amount} on {self.date:%Y-%m-%d}"

    def clean(self):
        super().clean()

        if self.amount <= Decimal("0.00"):
            raise ValidationError({
                "amount": "Payment amount must be greater than zero."
            })

        remaining = self.payment.course_fee - self.payment.amount_paid

        if self.amount > remaining:
            raise ValidationError({
                "amount": (
                    f"This payment exceeds the course fee.\n\n"
                    f"Course Fee: ₦{self.payment.course_fee:,.2f}\n"
                    f"Paid So Far: ₦{self.payment.amount_paid:,.2f}\n"
                    f"Remaining Balance: ₦{remaining:,.2f}\n"
                    f"Attempted Top-up: ₦{self.amount:,.2f}\n\n"
                    f"You can only accept a maximum payment of ₦{remaining:,.2f}."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)