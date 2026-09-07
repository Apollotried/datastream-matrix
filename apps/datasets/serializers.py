from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from apps.datasets.models import Dataset, DatasetRecord, DatasetStatus


class DatasetUploadSerializer(serializers.ModelSerializer):
    """Validate dataset uploads and serialize created dataset metadata."""

    file = serializers.FileField(write_only=True)

    def validate_file(self, uploaded_file: UploadedFile) -> UploadedFile:
        """Validate dataset upload file before creating a Dataset."""
        original_filename = uploaded_file.name or ""
        extension = Path(original_filename).suffix.lower()
        allowed_extensions = {
            value.lower() for value in settings.DATASET_UPLOAD_ALLOWED_EXTENSIONS
        }

        if not original_filename:
            raise serializers.ValidationError("Uploaded file must have a filename.")

        if extension not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise serializers.ValidationError(
                f"Unsupported file extension '{extension}'. Allowed: {allowed}."
            )

        if uploaded_file.size == 0:
            raise serializers.ValidationError("Uploaded file cannot be empty.")

        if uploaded_file.size > settings.DATASET_UPLOAD_MAX_SIZE_BYTES:
            raise serializers.ValidationError(
                f"Uploaded file cannot exceed {settings.DATASET_UPLOAD_MAX_SIZE_BYTES} bytes."
            )

        return uploaded_file

    class Meta:
        model = Dataset
        fields = (
            "id",
            "file",
            "original_filename",
            "status",
            "created_at",
        )
        read_only_fields = (
            "id",
            "original_filename",
            "status",
            "created_at",
        )


class DatasetStatusSerializer(serializers.ModelSerializer):
    """Serialize dataset processing progress for polling clients."""

    class Meta:
        model = Dataset
        fields = (
            "id",
            "status",
            "total_rows",
            "processed_rows",
            "failed_rows",
            "celery_task_id",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DatasetRowErrorSerializer(serializers.Serializer):
    """Serialize invalid row details stored in MongoDB."""

    dataset_id = serializers.CharField()
    row_number = serializers.IntegerField()
    raw_data = serializers.DictField()
    errors = serializers.ListField(child=serializers.CharField())
    created_at = serializers.DateTimeField()


class DatasetRecordSerializer(serializers.ModelSerializer):
    """Serialize valid parsed dataset records stored in PostgreSQL."""

    class Meta:
        model = DatasetRecord
        fields = (
            "id",
            "dataset",
            "customer_email",
            "product_name",
            "quantity",
            "unit_price",
            "purchased_at",
            "row_number",
            "created_at",
        )
        read_only_fields = fields


class DatasetRecordFilterSerializer(serializers.Serializer):
    """Validate dataset record list query parameters."""

    customer_email = serializers.EmailField(required=False)
    purchased_at_from = serializers.DateField(required=False)
    purchased_at_to = serializers.DateField(required=False)

    def validate(self, attrs):
        """Ensure date range filters are chronologically valid."""
        purchased_at_from = attrs.get("purchased_at_from")
        purchased_at_to = attrs.get("purchased_at_to")

        if (
            purchased_at_from
            and purchased_at_to
            and purchased_at_from > purchased_at_to
        ):
            raise serializers.ValidationError(
                "purchased_at_from cannot be after purchased_at_to."
            )

        return attrs


class DatasetListFilterSerializer(serializers.Serializer):
    """Validate dataset list query parameters."""

    status = serializers.ChoiceField(
        choices=DatasetStatus.choices,
        required=False,
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )


class DatasetListSerializer(serializers.ModelSerializer):
    """Serialize dataset summaries for list views."""

    class Meta:
        model = Dataset
        fields = (
            "id",
            "original_filename",
            "status",
            "total_rows",
            "processed_rows",
            "failed_rows",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
