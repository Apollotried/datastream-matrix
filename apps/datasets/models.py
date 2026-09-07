from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class DatasetStatus(models.TextChoices):
    """Lifecycle states for an uploaded dataset."""

    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class Dataset(models.Model):
    """Metadata and processing state for an uploaded dataset file."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="datasets/%Y/%m/%d/")
    status = models.CharField(
        max_length=20,
        choices=DatasetStatus.choices,
        default=DatasetStatus.PENDING,
    )
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    file_deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.status})"


class DatasetRecord(models.Model):
    """Validated sales transaction row parsed from an uploaded dataset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="records",
    )
    customer_email = models.EmailField()
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    purchased_at = models.DateField()
    row_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["dataset", "row_number"]),
            models.Index(fields=["customer_email"]),
            models.Index(fields=["purchased_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.customer_email} - {self.product_name}"