# Generated manually on 2026-06-10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_remove_old_certificates'),
    ]

    operations = [
        # Remove unique_together constraint first
        migrations.AlterUniqueTogether(
            name='certificate',
            unique_together=set(),
        ),
        # Remove old fields
        migrations.RemoveField(
            model_name='certificate',
            name='registration',
        ),
        migrations.RemoveField(
            model_name='certificate',
            name='certificate_type',
        ),
        migrations.RemoveField(
            model_name='certificate',
            name='course',
        ),
        # Add new enrollment field
        migrations.AddField(
            model_name='certificate',
            name='enrollment',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='certificate',
                to='app.enrollment'
            ),
        ),
        # Update certificate_file upload path
        migrations.AlterField(
            model_name='certificate',
            name='certificate_file',
            field=models.FileField(blank=True, null=True, upload_to='certificates/'),
        ),
        # Update field help texts
        migrations.AlterField(
            model_name='certificate',
            name='completion_percentage',
            field=models.FloatField(help_text='Course completion percentage'),
        ),
        migrations.AlterField(
            model_name='certificate',
            name='average_grade',
            field=models.FloatField(blank=True, help_text='Average grade for this course', null=True),
        ),
    ]
