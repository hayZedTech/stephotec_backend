import os
import django
import sys

sys.path.append('c:\\stephotec_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.apps import apps
from django.db import transaction

def clear_students():
    print("Clearing all student records...")
    User = apps.get_model('accounts', 'User')
    StudentCourse = apps.get_model('accounts', 'StudentCourse')
    Payment = apps.get_model('payments', 'Payment')

    with transaction.atomic():
        # Delete payments associated with students
        p_count = Payment.objects.all().count()
        Payment.objects.all().delete()
        print(f"Deleted {p_count} payment records.")

        # Delete student courses
        sc_count = StudentCourse.objects.all().count()
        StudentCourse.objects.all().delete()
        print(f"Deleted {sc_count} student course records.")

        # Delete all student users
        students = User.all_objects.filter(role='STUDENT')
        s_count = students.count()
        students.delete()
        print(f"Deleted {s_count} student user accounts.")

    print("All student tables cleared successfully!")

if __name__ == "__main__":
    clear_students()
