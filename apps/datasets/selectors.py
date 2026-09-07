from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.datasets.models import Dataset, DatasetRecord
from apps.datasets.mongodb_logging import DATASET_ROW_ERRORS_COLLECTION
from common.mongodb import get_mongo_database


def get_dataset_for_user(
    *,
    dataset_id: str,
    owner: AbstractBaseUser,
) -> Dataset:
    """Return a dataset owned by the given user or raise 404."""
    return get_object_or_404(
        Dataset,
        id=dataset_id,
        owner=owner,
    )


def list_datasets_for_user(
    *,
    owner: AbstractBaseUser,
    status: str | None = None,
    search: str | None = None,
) -> QuerySet[Dataset]:
    """Return datasets owned by the given user, optionally filtered."""
    queryset = Dataset.objects.filter(owner=owner)

    if status:
        queryset = queryset.filter(status=status)

    if search:
        queryset = queryset.filter(original_filename__icontains=search)

    return queryset.order_by("-created_at")


def list_dataset_records(
    *,
    dataset: Dataset,
    customer_email: str | None = None,
    purchased_at_from: object | None = None,
    purchased_at_to: object | None = None,
) -> QuerySet[DatasetRecord]:
    """Return valid parsed records for a dataset, optionally filtered."""
    queryset = DatasetRecord.objects.filter(dataset=dataset)

    if customer_email:
        queryset = queryset.filter(customer_email=customer_email)

    if purchased_at_from:
        queryset = queryset.filter(purchased_at__gte=purchased_at_from)

    if purchased_at_to:
        queryset = queryset.filter(purchased_at__lte=purchased_at_to)

    return queryset.order_by("row_number")


def list_dataset_row_errors(*, dataset_id: str) -> list[dict[str, Any]]:
    """Return MongoDB row validation errors for a dataset."""
    db = get_mongo_database()
    return list(
        db[DATASET_ROW_ERRORS_COLLECTION]
        .find({"dataset_id": dataset_id}, {"_id": 0})
        .sort("row_number", 1)
    )
