from django.db import migrations


CLEANUP_TASK_NAME = "Purge old dataset uploads"
CLEANUP_TASK_PATH = "apps.datasets.tasks.purge_old_dataset_uploads"


def create_cleanup_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="hours",
    )

    PeriodicTask.objects.update_or_create(
        name=CLEANUP_TASK_NAME,
        defaults={
            "task": CLEANUP_TASK_PATH,
            "interval": interval,
            "enabled": True,
        },
    )


def remove_cleanup_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=CLEANUP_TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
        ("datasets", "0003_dataset_file_deleted_at"),
    ]

    operations = [
        migrations.RunPython(
            create_cleanup_periodic_task,
            remove_cleanup_periodic_task,
        ),
    ]