from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import BinaryIO


from django.conf import settings

import pandas as pd
import xlsxwriter
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.datasets.models import Dataset, DatasetRecord, DatasetStatus
from apps.datasets.mongodb_logging import (
    DATASET_ROW_ERRORS_COLLECTION,
    log_dataset_row_error,
)
from apps.datasets.selectors import list_dataset_records, list_dataset_row_errors
from common.mongodb import get_mongo_database


REQUIRED_SALES_COLUMNS = {
    "customer_email",
    "product_name",
    "quantity",
    "unit_price",
    "purchased_at",
}


def build_dataset_record_from_row(
    *,
    dataset: Dataset,
    row_data: dict[str, object],
    row_number: int,
) -> tuple[DatasetRecord | None, list[str]]:
    """Build a DatasetRecord from raw row data, returning validation errors."""
    errors: list[str] = []

    customer_email = str(row_data.get("customer_email", "")).strip()
    product_name = str(row_data.get("product_name", "")).strip()
    raw_quantity = row_data.get("quantity")
    raw_unit_price = row_data.get("unit_price")
    raw_purchased_at = row_data.get("purchased_at")

    try:
        validate_email(customer_email)
    except ValidationError:
        errors.append("customer_email must be a valid email address.")

    if not product_name:
        errors.append("product_name is required.")

    try:
        quantity = int(raw_quantity)
        if quantity <= 0:
            errors.append("quantity must be greater than zero.")
    except (TypeError, ValueError):
        quantity = 0
        errors.append("quantity must be an integer.")

    try:
        unit_price = Decimal(str(raw_unit_price))
        if unit_price < 0:
            errors.append("unit_price must be zero or greater.")
    except Exception:
        unit_price = Decimal("0")
        errors.append("unit_price must be a valid decimal number.")

    try:
        purchased_at = pd.to_datetime(raw_purchased_at).date()
    except Exception:
        purchased_at = None
        errors.append("purchased_at must be a valid date.")

    if errors:
        return None, errors

    return (
        DatasetRecord(
            dataset=dataset,
            customer_email=customer_email,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            purchased_at=purchased_at,
            row_number=row_number,
        ),
        [],
    )


def process_dataset_file(*, dataset_id: str) -> None:
    """Parse an uploaded sales CSV and store validated records."""
    dataset = Dataset.objects.get(id=dataset_id)
    dataset.status = DatasetStatus.PROCESSING
    dataset.save(update_fields=["status", "updated_at"])

    file_path = Path(dataset.file.path)
    total_rows = 0
    processed_rows = 0
    failed_rows = 0

    for chunk in pd.read_csv(file_path, chunksize=5000):
        missing_columns = REQUIRED_SALES_COLUMNS.difference(chunk.columns)

        if missing_columns:
            dataset.status = DatasetStatus.FAILED
            dataset.error_message = (
                f"Missing required columns: {', '.join(sorted(missing_columns))}"
            )
            dataset.save(update_fields=["status", "error_message", "updated_at"])
            return

        records: list[DatasetRecord] = []

        for row_offset, row_data in enumerate(chunk.to_dict(orient="records"), start=1):
            row_number = total_rows + row_offset
            record, errors = build_dataset_record_from_row(
                dataset=dataset,
                row_data=row_data,
                row_number=row_number,
            )

            if record is None:
                failed_rows += 1
                log_dataset_row_error(
                    dataset_id=str(dataset.id),
                    row_number=row_number,
                    raw_data=row_data,
                    errors=errors,
                )
                continue

            records.append(record)

        DatasetRecord.objects.bulk_create(records, batch_size=1000)

        total_rows += len(chunk)
        processed_rows += len(records)

        Dataset.objects.filter(id=dataset.id).update(
            total_rows=total_rows,
            processed_rows=processed_rows,
            failed_rows=failed_rows,
            updated_at=timezone.now(),
        )

    Dataset.objects.filter(id=dataset.id).update(
        status=DatasetStatus.COMPLETED,
        total_rows=total_rows,
        processed_rows=processed_rows,
        failed_rows=failed_rows,
        updated_at=timezone.now(),
    )


@transaction.atomic
def create_dataset_upload(
    *,
    owner: AbstractBaseUser,
    uploaded_file: BinaryIO,
) -> Dataset:
    """Create a dataset upload record and enqueue asynchronous processing."""
    dataset = Dataset.objects.create(
        owner=owner,
        original_filename=uploaded_file.name,
        file=uploaded_file,
    )

    from apps.datasets.tasks import process_dataset_upload

    transaction.on_commit(lambda: process_dataset_upload.delay(str(dataset.id)))
    return dataset


@transaction.atomic
def retry_dataset_processing(*, dataset: Dataset) -> Dataset:
    """Reset a pending/failed dataset and enqueue processing again."""
    if dataset.status not in {
        DatasetStatus.PENDING,
        DatasetStatus.FAILED,
    }:
        raise ValueError("Only pending or failed datasets can be retried.")

    DatasetRecord.objects.filter(dataset=dataset).delete()

    db = get_mongo_database()
    db[DATASET_ROW_ERRORS_COLLECTION].delete_many({"dataset_id": str(dataset.id)})

    dataset.status = DatasetStatus.PENDING
    dataset.total_rows = 0
    dataset.processed_rows = 0
    dataset.failed_rows = 0
    dataset.celery_task_id = ""
    dataset.error_message = ""
    dataset.save(
        update_fields=[
            "status",
            "total_rows",
            "processed_rows",
            "failed_rows",
            "celery_task_id",
            "error_message",
            "updated_at",
        ]
    )

    from apps.datasets.tasks import process_dataset_upload

    transaction.on_commit(lambda: process_dataset_upload.delay(str(dataset.id)))
    return dataset


def build_dataset_export_workbook(*, dataset: Dataset) -> BytesIO:
    """Build an Excel workbook containing dataset summary, records, and errors."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})

    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#1F2937",
            "font_color": "#FFFFFF",
            "border": 1,
        }
    )
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    money_format = workbook.add_format({"num_format": "$#,##0.00"})

    summary_sheet = workbook.add_worksheet("Summary")
    summary_rows = [
        ("Dataset ID", str(dataset.id)),
        ("Original Filename", dataset.original_filename),
        ("Status", dataset.status),
        ("Total Rows", dataset.total_rows),
        ("Processed Rows", dataset.processed_rows),
        ("Failed Rows", dataset.failed_rows),
        ("Created At", dataset.created_at.isoformat()),
        ("Updated At", dataset.updated_at.isoformat()),
    ]

    summary_sheet.write_row(0, 0, ["Field", "Value"], header_format)
    for row_index, row in enumerate(summary_rows, start=1):
        summary_sheet.write_row(row_index, 0, row)

    summary_sheet.set_column(0, 0, 24)
    summary_sheet.set_column(1, 1, 48)

    records_sheet = workbook.add_worksheet("Valid Records")
    record_headers = [
        "Row Number",
        "Customer Email",
        "Product Name",
        "Quantity",
        "Unit Price",
        "Purchased At",
    ]
    records_sheet.write_row(0, 0, record_headers, header_format)

    records = list_dataset_records(dataset=dataset)
    for row_index, record in enumerate(records, start=1):
        records_sheet.write(row_index, 0, record.row_number)
        records_sheet.write(row_index, 1, record.customer_email)
        records_sheet.write(row_index, 2, record.product_name)
        records_sheet.write(row_index, 3, record.quantity)
        records_sheet.write(row_index, 4, float(record.unit_price), money_format)
        records_sheet.write_datetime(row_index, 5, record.purchased_at, date_format)

    records_sheet.set_column(0, 0, 12)
    records_sheet.set_column(1, 1, 28)
    records_sheet.set_column(2, 2, 24)
    records_sheet.set_column(3, 4, 14)
    records_sheet.set_column(5, 5, 16)

    errors_sheet = workbook.add_worksheet("Invalid Rows")
    error_headers = ["Row Number", "Raw Data", "Errors", "Created At"]
    errors_sheet.write_row(0, 0, error_headers, header_format)

    row_errors = list_dataset_row_errors(dataset_id=str(dataset.id))
    for row_index, row_error in enumerate(row_errors, start=1):
        errors_sheet.write(row_index, 0, row_error["row_number"])
        errors_sheet.write(row_index, 1, str(row_error["raw_data"]))
        errors_sheet.write(row_index, 2, "; ".join(row_error["errors"]))
        errors_sheet.write(row_index, 3, row_error["created_at"].isoformat())

    errors_sheet.set_column(0, 0, 12)
    errors_sheet.set_column(1, 1, 64)
    errors_sheet.set_column(2, 2, 64)
    errors_sheet.set_column(3, 3, 28)

    workbook.close()
    output.seek(0)
    return output


def purge_old_dataset_upload_files() -> int:
    """Delete uploaded files older than the configured retention window."""
    
    cutoff = timezone.now() - timezone.timedelta(
        hours=settings.DATASET_UPLOAD_RETENTION_HOURS
    )

    old_datasets = Dataset.objects.filter(
        created_at__lt=cutoff,
        file_deleted_at__isnull=True,
    ).exclude(file="")

    deleted_count = 0

    for dataset in old_datasets.iterator():
        if dataset.file:
            dataset.file.delete(save=False)
            dataset.file_deleted_at = timezone.now()
            dataset.save(update_fields=["file", "file_deleted_at", "updated_at"])
            deleted_count += 1

    return deleted_count
