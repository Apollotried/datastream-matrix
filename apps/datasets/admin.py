from django.contrib import admin

from apps.datasets.models import Dataset, DatasetRecord


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin configuration for uploaded datasets."""

    list_display = (
        "id",
        "original_filename",
        "owner",
        "status",
        "processed_rows",
        "failed_rows",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("original_filename", "owner__email", "celery_task_id")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)



@admin.register(DatasetRecord)
class DatasetRecordAdmin(admin.ModelAdmin):
    """Admin configuration for parsed dataset records."""

    list_display = (
        "id",
        "dataset",
        "customer_email",
        "product_name",
        "quantity",
        "unit_price",
        "purchased_at",
        "row_number",
    )
    list_filter = ("purchased_at",)
    search_fields = ("customer_email", "product_name", "dataset__original_filename")
    readonly_fields = ("id", "created_at")
    ordering = ("dataset", "row_number")