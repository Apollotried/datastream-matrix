from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.datasets.models import Dataset
from unittest.mock import patch

from django.test import TestCase


User = get_user_model()


class DatasetUploadAPITests(APITestCase):
    """Tests for dataset upload API behavior."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="strong-test-password",
        )
        self.url = reverse("dataset-upload")

    def test_upload_requires_authentication(self) -> None:
        file = SimpleUploadedFile(
            "sales.csv",
            b"customer_email,product_name,quantity,unit_price,purchased_at\n",
            content_type="text/csv",
        )

        response = self.client.post(self.url, {"file": file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Dataset.objects.count(), 0)

    def test_upload_rejects_invalid_file_extension(self) -> None:
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile(
            "notes.txt",
            b"hello",
            content_type="text/plain",
        )

        response = self.client.post(self.url, {"file": file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Dataset.objects.count(), 0)
        self.assertIn("file", response.data["error"]["details"])


    @patch("apps.datasets.tasks.process_dataset_upload.delay")
    def test_upload_creates_dataset_and_queues_processing(self, mock_delay) -> None:
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile(
            "sales.csv",
            b"customer_email,product_name,quantity,unit_price,purchased_at\n"
            b"alice@example.com,Laptop,1,1200.00,2026-08-20\n",
            content_type="text/csv",
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, {"file": file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.get()
        self.assertEqual(dataset.owner, self.user)
        self.assertEqual(dataset.original_filename, "sales.csv")
        self.assertEqual(dataset.status, "PENDING")
        mock_delay.assert_called_once_with(str(dataset.id))