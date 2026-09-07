from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.datasets.models import Dataset, DatasetStatus
from apps.datasets.services import process_dataset_file, purge_old_dataset_upload_files


@shared_task(bind=True)
def process_dataset_upload(self, dataset_id: str) -> None:
    """Process an uploaded dataset file asynchronously."""
    Dataset.objects.filter(id=dataset_id).update(
        status=DatasetStatus.PROCESSING,
        celery_task_id=self.request.id or "",
        updated_at=timezone.now(),
    )

    try:
        process_dataset_file(dataset_id=dataset_id)
    except Exception as exc:
        Dataset.objects.filter(id=dataset_id).update(
            status=DatasetStatus.FAILED,
            error_message=str(exc),
            updated_at=timezone.now(),
        )
        raise


@shared_task
def purge_old_dataset_uploads() -> int:
    """Delete uploaded dataset files older than the configured retention window."""
    
    return purge_old_dataset_upload_files()