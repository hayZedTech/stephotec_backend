# Generated migration for StudentCourse model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_user_managers_user_deleted_at_user_deleted_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentCourse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enrollment_id', models.CharField(max_length=30, unique=True)),
                ('admission_year', models.PositiveIntegerField(choices=[(2020, 2020), (2021, 2021), (2022, 2022), (2023, 2023), (2024, 2024), (2025, 2025)])),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('COMPLETED', 'Completed'), ('WITHDRAWN', 'Withdrawn')], default='ACTIVE', max_length=20)),
                ('started_at', models.DateField(auto_now_add=True)),
                ('completed_at', models.DateField(blank=True, null=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='students', to='accounts.course')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
    ]
