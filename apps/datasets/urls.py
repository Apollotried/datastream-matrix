from django.urls import path

from apps.datasets.views import (
    DatasetExportAPIView,
    DatasetListAPIView,
    DatasetRecordsAPIView,
    DatasetRetryAPIView,
    DatasetRowErrorsAPIView,
    DatasetStatusAPIView,
    DatasetUploadAPIView,
)

urlpatterns = [
    path("", DatasetListAPIView.as_view(), name="dataset-list"),
    path("upload/", DatasetUploadAPIView.as_view(), name="dataset-upload"),
    path("<uuid:dataset_id>/status/", DatasetStatusAPIView.as_view(), name="dataset-status"),
    path("<uuid:dataset_id>/errors/", DatasetRowErrorsAPIView.as_view(), name="dataset-row-errors"),
    path("<uuid:dataset_id>/records/", DatasetRecordsAPIView.as_view(), name="dataset-records"),
    path("<uuid:dataset_id>/retry/", DatasetRetryAPIView.as_view(), name="dataset-retry"),
    path("<uuid:dataset_id>/export/", DatasetExportAPIView.as_view(), name="dataset-export"),
]