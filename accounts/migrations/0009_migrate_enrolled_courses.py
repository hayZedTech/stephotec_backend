# Data migration to move enrolled_course from User to StudentCourse

from django.db import migrations


def migrate_enrolled_courses(apps, schema_editor):
    """Move enrolled_course data from User to StudentCourse"""
    User = apps.get_model('accounts', 'User')
    StudentCourse = apps.get_model('accounts', 'StudentCourse')
    
    for user in User.objects.filter(enrolled_course__isnull=False):
        # Create StudentCourse record for each user with enrolled_course
        sc, created = StudentCourse.objects.get_or_create(
            student=user,
            course=user.enrolled_course,
            admission_year=user.admission_year or 2024,
            defaults={
                'is_primary': True,
                'enrollment_id': '',  # Will be set below
            }
        )
        # Generate enrollment_id if not set
        if created and not sc.enrollment_id:
            short_year = str(sc.admission_year)[-2:]
            prefix = f"{sc.course.code_prefix}/{short_year}/"
            last = (
                StudentCourse.objects.filter(
                    course=sc.course,
                    admission_year=sc.admission_year,
                    enrollment_id__startswith=prefix,
                )
                .order_by("enrollment_id")
                .last()
            )
            if last:
                sequence = int(last.enrollment_id.split("/")[-1]) + 1
            else:
                sequence = 1
            sc.enrollment_id = f"{prefix}{sequence:04d}"
            sc.save()


def reverse_migrate(apps, schema_editor):
    """Reverse migration - delete StudentCourse records"""
    StudentCourse = apps.get_model('accounts', 'StudentCourse')
    StudentCourse.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_studentcourse'),
    ]

    operations = [
        migrations.RunPython(migrate_enrolled_courses, reverse_migrate),
    ]
