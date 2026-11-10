from django.db import migrations


def populate_complaint_numbers(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    for complaint in Complaint.objects.filter(complaint_number__isnull=True).iterator():
        year = complaint.created_at.year
        complaint.complaint_number = f"CIV-{year}-{complaint.pk:08d}"
        complaint.save(update_fields=["complaint_number"])


def clear_complaint_numbers(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    Complaint.objects.update(complaint_number=None)


class Migration(migrations.Migration):
    dependencies = [("complaints", "0007_complaint_complaint_number")]

    operations = [
        migrations.RunPython(populate_complaint_numbers, clear_complaint_numbers),
    ]
