from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files import File
from django.test import TestCase
from django.utils import timezone

from apps.datasets.models import Dataset, DatasetRecord, DatasetStatus
from apps.datasets.services import process_dataset_file, purge_old_dataset_upload_files

User = get_user_model()


class DatasetProcessingServiceTests(TestCase):
    """Tests for dataset processing service behavior."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="service-owner@example.com",
            password="strong-test-password",
        )

    @patch("apps.datasets.services.log_dataset_row_error")
    def test_process_dataset_file_stores_valid_rows_and_logs_invalid_rows(
        self,
        mock_log_dataset_row_error,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sales_mixed.csv"
            csv_path.write_text(
                "customer_email,product_name,quantity,unit_price,purchased_at\n"
                "alice@example.com,Laptop,1,1200.00,2026-08-20\n"
                "bad-email,Mouse,wrong,25.50,not-a-date\n",
                encoding="utf-8",
            )

            with csv_path.open("rb") as csv_file:
                dataset = Dataset.objects.create(
                    owner=self.user,
                    original_filename="sales_mixed.csv",
                    file=File(csv_file, name="sales_mixed.csv"),
                )

        process_dataset_file(dataset_id=str(dataset.id))

        dataset.refresh_from_db()

        self.assertEqual(dataset.status, DatasetStatus.COMPLETED)
        self.assertEqual(dataset.total_rows, 2)
        self.assertEqual(dataset.processed_rows, 1)
        self.assertEqual(dataset.failed_rows, 1)

        self.assertEqual(DatasetRecord.objects.filter(dataset=dataset).count(), 1)
        record = DatasetRecord.objects.get(dataset=dataset)
        self.assertEqual(record.customer_email, "alice@example.com")
        self.assertEqual(record.product_name, "Laptop")
        self.assertEqual(record.row_number, 1)

        mock_log_dataset_row_error.assert_called_once()
        _, kwargs = mock_log_dataset_row_error.call_args
        self.assertEqual(kwargs["dataset_id"], str(dataset.id))
        self.assertEqual(kwargs["row_number"], 2)
        self.assertIn("quantity must be an integer.", kwargs["errors"])

    def test_purge_old_dataset_upload_files_deletes_only_expired_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old_file_path = Path(temp_dir) / "old.csv"
            old_file_path.write_text(
                "customer_email,product_name,quantity,unit_price,purchased_at\n",
                encoding="utf-8",
            )

            recent_file_path = Path(temp_dir) / "recent.csv"
            recent_file_path.write_text(
                "customer_email,product_name,quantity,unit_price,purchased_at\n",
                encoding="utf-8",
            )

            with old_file_path.open("rb") as old_file:
                old_dataset = Dataset.objects.create(
                    owner=self.user,
                    original_filename="old.csv",
                    file=File(old_file, name="old.csv"),
                )

            with recent_file_path.open("rb") as recent_file:
                recent_dataset = Dataset.objects.create(
                    owner=self.user,
                    original_filename="recent.csv",
                    file=File(recent_file, name="recent.csv"),
                )

            old_dataset.created_at = timezone.now() - timedelta(hours=25)
            old_dataset.save(update_fields=["created_at"])

            deleted_count = purge_old_dataset_upload_files()

            old_dataset.refresh_from_db()
            recent_dataset.refresh_from_db()

            self.assertEqual(deleted_count, 1)
            self.assertEqual(old_dataset.file.name, "")
            self.assertIsNotNone(old_dataset.file_deleted_at)
            self.assertNotEqual(recent_dataset.file.name, "")
            self.assertIsNone(recent_dataset.file_deleted_at)
