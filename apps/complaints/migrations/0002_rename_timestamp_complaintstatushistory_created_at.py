from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("complaints", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="complaintstatushistory",
            old_name="timestamp",
            new_name="created_at",
        ),
        migrations.AlterField(
            model_name="complaintstatushistory",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]