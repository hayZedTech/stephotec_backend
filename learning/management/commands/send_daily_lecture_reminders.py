from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from learning.models import LectureSchedule
from notifications.services import send_student_notification

User = get_user_model()


class Command(BaseCommand):
    help = "Sends daily lecture reminders to students who have classes scheduled today"

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        DAYS_MAP = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        today_day_name = DAYS_MAP[now.weekday()]

        self.stdout.write(f"Checking lecture schedules for today: {today_day_name} ({now.strftime('%Y-%m-%d')})...")

        schedules = LectureSchedule.objects.filter(
            days_of_week__contains=[today_day_name],
            is_active=True
        ).select_related("course").prefetch_related("assigned_groups__members", "assigned_students", "course__students__student")

        if not schedules.exists():
            self.stdout.write("No active classes scheduled for today.")
            return

        total_notifications_sent = 0

        for sched in schedules:
            # Collect all distinct students
            student_ids = set()

            has_direct = sched.assigned_students.exists()
            has_groups = sched.assigned_groups.exists()

            # 1. Direct students
            for s in sched.assigned_students.all():
                student_ids.add(s.id)

            # 2. Group members
            for g in sched.assigned_groups.all():
                for m in g.members.all():
                    student_ids.add(m.id)

            # 3. Course enrolled students (only if no specific groups or direct students are assigned)
            if not has_direct and not has_groups and sched.course:
                for sc in sched.course.students.all():
                    if sc.student_id:
                        student_ids.add(sc.student_id)

            # Determine timing for today
            start_t = sched.start_time
            end_t = sched.end_time
            if sched.day_times and isinstance(sched.day_times, list):
                for dt in sched.day_times:
                    if str(dt.get("day", "")).upper() == today_day_name:
                        st_s = dt.get("start_time")
                        et_s = dt.get("end_time")
                        if st_s:
                            st_parts = [int(p) for p in st_s.split(":")[:2]]
                            start_t = timezone.datetime.min.time().replace(hour=st_parts[0], minute=st_parts[1])
                        if et_s:
                            et_parts = [int(p) for p in et_s.split(":")[:2]]
                            end_t = timezone.datetime.min.time().replace(hour=et_parts[0], minute=et_parts[1])
                        break

            start_formatted = start_t.strftime("%I:%M %p").lstrip("0") if start_t else ""
            end_formatted = end_t.strftime("%I:%M %p").lstrip("0") if end_t else ""
            time_str = f"{start_formatted} - {end_formatted}" if start_formatted and end_formatted else ""
            mode_desc = f" ({sched.get_mode_display()})" if sched.mode else ""
            location_info = f" at {sched.venue_or_link}" if sched.venue_or_link else ""

            msg = (
                f"Reminder: You have a class '{sched.title}' today, {today_day_name.capitalize()} "
                f"from {time_str}{mode_desc}{location_info}. Please check your lecture timetable."
            )

            for sid in student_ids:
                try:
                    student = User.objects.get(id=sid)
                    send_student_notification(
                        student=student,
                        title=f"Class Today: {sched.title} ({start_formatted})",
                        message=msg,
                        notification_type="INFO",
                        created_by=sched.created_by,
                        event_key="email_general",
                    )
                    total_notifications_sent += 1
                except User.DoesNotExist:
                    pass

        self.stdout.write(self.style.SUCCESS(f"Successfully sent {total_notifications_sent} daily lecture reminders."))
