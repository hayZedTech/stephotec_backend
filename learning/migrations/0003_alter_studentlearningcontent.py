# Generated migration for StudentLearningContent model change

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_remove_user_enrolled_course_and_admission_year'),
        ('learning', '0002_studentassignment_studentcertificate_studenthandout_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='StudentLearningContent',
        ),
        migrations.CreateModel(
            name='StudentLearningContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('learning_content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_to_students', to='learning.learningcontent')),
                ('student_course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_learning_contents', to='accounts.studentcourse')),
            ],
            options={
                'ordering': ['-assigned_at'],
                'unique_together': {('student_course', 'learning_content')},
            },
        ),
    ]
