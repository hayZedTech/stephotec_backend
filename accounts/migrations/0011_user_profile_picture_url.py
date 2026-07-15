# Generated migration for profile_picture_url field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_remove_user_enrolled_course_and_admission_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='profile_picture_url',
            field=models.URLField(blank=True, help_text='Cloudinary URL for profile picture', null=True),
        ),
    ]
