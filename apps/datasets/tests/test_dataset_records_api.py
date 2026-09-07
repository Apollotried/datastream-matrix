from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.datasets.models import Dataset, DatasetRecord, DatasetStatus

User = get_user_model()


class DatasetRecordsFilterAPITests(APITestCase):
    """Tests for dataset records API filtering behavior."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="records-filter-owner@example.com",
            password="strong-test-password",
        )
        self.dataset = Dataset.objects.create(
            owner=self.owner,
            original_filename="sales.csv",
            file="datasets/test/sales.csv",
            status=DatasetStatus.COMPLETED,
        )
        self.alice_record = DatasetRecord.objects.create(
            dataset=self.dataset,
            customer_email="alice@example.com",
            product_name="Laptop",
            quantity=1,
            unit_price="1200.00",
            purchased_at="2026-08-20",
            row_number=1,
        )
        self.bob_record = DatasetRecord.objects.create(
            dataset=self.dataset,
            customer_email="bob@example.com",
            product_name="Mouse",
            quantity=2,
            unit_price="25.50",
            purchased_at="2026-08-25",
            row_number=2,
        )
        self.url = reverse("dataset-records", kwargs={"dataset_id": self.dataset.id})

    def test_records_filter_by_customer_email(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url, {"customer_email": "alice@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.alice_record.id))

    def test_records_filter_by_purchased_at_range(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            self.url,
            {
                "purchased_at_from": "2026-08-24",
                "purchased_at_to": "2026-08-31",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.bob_record.id))

    def test_records_reject_invalid_date_range(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            self.url,
            {
                "purchased_at_from": "2026-08-31",
                "purchased_at_to": "2026-08-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["error"]["details"])
