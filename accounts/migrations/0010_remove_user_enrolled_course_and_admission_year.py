# Remove enrolled_course and admission_year from User model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_migrate_enrolled_courses'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='enrolled_course',
        ),
        migrations.RemoveField(
            model_name='user',
            name='admission_year',
        ),
    ]
