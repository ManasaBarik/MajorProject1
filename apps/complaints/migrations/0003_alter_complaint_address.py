from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("complaints", "0002_rename_timestamp_complaintstatushistory_created_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="complaint",
            name="address",
            field=models.TextField(blank=True),
        ),
    ]