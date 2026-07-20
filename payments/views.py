from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdminUserRole
from accounts.models import StudentCourse, User
from .models import Payment, PaymentEntry
from .serializers import PaymentSerializer, PaymentEntrySerializer, StudentPaymentSummarySerializer
from decimal import Decimal


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return Payment.objects.select_related(
            "student_course__student",
            "student_course__course",
        ).all()

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        """Return all payment entries for a specific payment record."""
        payment = self.get_object()
        entries = payment.entries.select_related("recorded_by").all()
        serializer = PaymentEntrySerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="history/add")
    def add_entry(self, request, pk=None):
        """Add a new payment entry and update the payment's amount_paid."""
        payment = self.get_object()
        serializer = PaymentEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(payment=payment, recorded_by=request.user)
        # Recalculate total amount paid from all entries
        total = sum(e.amount for e in payment.entries.all())
        payment.amount_paid = total
        payment.save()
        return Response(PaymentEntrySerializer(entry).data, status=201)

    @action(detail=True, methods=["delete"], url_path="history/(?P<entry_pk>[^/.]+)/delete")
    def delete_entry(self, request, pk=None, entry_pk=None):
        """Delete a payment entry and recalculate amount_paid."""
        payment = self.get_object()
        try:
            entry = payment.entries.get(pk=entry_pk)
        except PaymentEntry.DoesNotExist:
            return Response({"detail": "Entry not found."}, status=404)
        entry.delete()
        total = sum(e.amount for e in payment.entries.all())
        payment.amount_paid = total
        payment.save()
        return Response(status=204)

    @action(detail=False, methods=["get"], url_path="my", permission_classes=[IsAuthenticated])
    def my_payments(self, request):
        """Return all payment records for the currently authenticated student."""
        payments = Payment.objects.select_related(
            "student_course__student",
            "student_course__course",
        ).filter(
            student_course__student=request.user
        ).order_by("-student_course__is_primary", "student_course__course__name")
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="ensure")
    def ensure_all(self, request):
        """Create missing Payment records for all StudentCourse entries."""
        created = 0
        for sc in StudentCourse.objects.all():
            _, was_created = Payment.objects.get_or_create(student_course=sc)
            if was_created:
                created += 1
        return Response({"created": created})

    @action(detail=False, methods=["get"], url_path="by_student")
    def by_student(self, request):
        """Return one summary row per student with all course payments nested."""
        payments = self.get_queryset().order_by(
            "student_course__student__first_name",
            "-student_course__is_primary",
        )

        # Group by student
        student_map = {}
        for p in payments:
            student = p.student_course.student
            sid = student.id
            if sid not in student_map:
                student_map[sid] = {
                    "student_id": sid,
                    "student_name": f"{student.first_name} {student.last_name}".strip() or student.username,
                    "student_username": student.username,
                    "primary_course_name": "",
                    "primary_course_fee": Decimal("0"),
                    "primary_amount_paid": Decimal("0"),
                    "primary_outstanding": Decimal("0"),
                    "primary_status": "UNPAID",
                    "courses": [],
                }
            student_map[sid]["courses"].append(p)
            if p.student_course.is_primary:
                student_map[sid]["primary_course_name"] = p.student_course.course.name
                student_map[sid]["primary_course_fee"] = p.course_fee
                student_map[sid]["primary_amount_paid"] = p.amount_paid
                student_map[sid]["primary_outstanding"] = p.outstanding
                student_map[sid]["primary_status"] = p.status

        # Fallback: if no primary course, use first course
        for sid, data in student_map.items():
            if not data["primary_course_name"] and data["courses"]:
                first = data["courses"][0]
                data["primary_course_name"] = first.student_course.course.name
                data["primary_course_fee"] = first.course_fee
                data["primary_amount_paid"] = first.amount_paid
                data["primary_outstanding"] = first.outstanding
                data["primary_status"] = first.status

        serializer = StudentPaymentSummarySerializer(list(student_map.values()), many=True)
        return Response(serializer.data)
