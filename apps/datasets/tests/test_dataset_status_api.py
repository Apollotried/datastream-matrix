from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.datasets.models import Dataset, DatasetRecord, DatasetStatus
User = get_user_model()


class DatasetStatusAPITests(APITestCase):
    """Tests for dataset status API behavior."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="strong-test-password",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="strong-test-password",
        )
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            original_filename="sales.csv",
            file="datasets/test/sales.csv",
            status=DatasetStatus.COMPLETED,
            total_rows=2,
            processed_rows=1,
            failed_rows=1,
            celery_task_id="task-123",
        )
        self.url = reverse("dataset-status", kwargs={"dataset_id": self.dataset.id})

    def test_status_requires_authentication(self) -> None:
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_view_dataset_status(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.dataset.id))
        self.assertEqual(response.data["status"], DatasetStatus.COMPLETED)
        self.assertEqual(response.data["total_rows"], 2)
        self.assertEqual(response.data["processed_rows"], 1)
        self.assertEqual(response.data["failed_rows"], 1)
        self.assertEqual(response.data["celery_task_id"], "task-123")

    def test_other_user_cannot_view_dataset_status(self) -> None:
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



class DatasetRecordsAPITests(APITestCase):
    """Tests for dataset records API behavior."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="records-owner@example.com",
            password="strong-test-password",
        )
        self.other_user = User.objects.create_user(
            email="records-other@example.com",
            password="strong-test-password",
        )
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            original_filename="sales.csv",
            file="datasets/test/sales.csv",
            status=DatasetStatus.COMPLETED,
        )
        self.record = DatasetRecord.objects.create(
            dataset=self.dataset,
            customer_email="alice@example.com",
            product_name="Laptop",
            quantity=1,
            unit_price="1200.00",
            purchased_at="2026-08-20",
            row_number=1,
        )
        self.url = reverse("dataset-records", kwargs={"dataset_id": self.dataset.id})

    def test_records_require_authentication(self) -> None:
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_view_dataset_records(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["customer_email"], "alice@example.com")

    def test_other_user_cannot_view_dataset_records(self) -> None:
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)