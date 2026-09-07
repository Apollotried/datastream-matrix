from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.datasets.models import Dataset, DatasetStatus

User = get_user_model()


class DatasetListAPITests(APITestCase):
    """Tests for dataset list API filtering behavior."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="list-owner@example.com",
            password="strong-test-password",
        )
        self.other_user = User.objects.create_user(
            email="list-other@example.com",
            password="strong-test-password",
        )
        self.completed_dataset = Dataset.objects.create(
            owner=self.owner,
            original_filename="sales_mixed.csv",
            file="datasets/test/sales_mixed.csv",
            status=DatasetStatus.COMPLETED,
        )
        self.pending_dataset = Dataset.objects.create(
            owner=self.owner,
            original_filename="inventory.csv",
            file="datasets/test/inventory.csv",
            status=DatasetStatus.PENDING,
        )
        Dataset.objects.create(
            owner=self.other_user,
            original_filename="other_sales.csv",
            file="datasets/test/other_sales.csv",
            status=DatasetStatus.COMPLETED,
        )
        self.url = reverse("dataset-list")

    def test_list_requires_authentication(self) -> None:
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_current_users_datasets(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_list_filters_by_status(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url, {"status": DatasetStatus.COMPLETED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.completed_dataset.id),
        )

    def test_list_filters_by_filename_search(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url, {"search": "sales"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.completed_dataset.id),
        )

    def test_list_rejects_invalid_status_filter(self) -> None:
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url, {"status": "INVALID"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data["error"]["details"])
