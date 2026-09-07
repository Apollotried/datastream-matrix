from __future__ import annotations

from collections.abc import Iterable

from django.http import FileResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from apps.datasets.selectors import (
    get_dataset_for_user,
    list_dataset_records,
    list_dataset_row_errors,
    list_datasets_for_user,
)
from apps.datasets.serializers import (
    DatasetListFilterSerializer,
    DatasetListSerializer,
    DatasetRecordFilterSerializer,
    DatasetRecordSerializer,
    DatasetRowErrorSerializer,
    DatasetStatusSerializer,
    DatasetUploadSerializer,
)
from apps.datasets.models import DatasetStatus
from apps.datasets.services import (
    build_dataset_export_workbook,
    create_dataset_upload,
    retry_dataset_processing,
)


def get_paginated_response(
    *,
    request: Request,
    view: APIView,
    items: Iterable[object],
    serializer_class: type[BaseSerializer],
) -> Response:
    """Serialize items with DRF page-number pagination."""
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(items, request, view=view)

    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


class DatasetListAPIView(APIView):
    """Return paginated datasets owned by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Datasets"],
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter datasets by processing status.",
                required=False,
                enum=DatasetStatus.values,
            ),
            OpenApiParameter(
                name="search",
                description="Filter datasets by original filename.",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: DatasetListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
        },
        description="Return paginated datasets owned by the current user.",
    )
    def get(self, request: Request) -> Response:
        filter_serializer = DatasetListFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        datasets = list_datasets_for_user(
            owner=request.user,
            status=filter_serializer.validated_data.get("status"),
            search=filter_serializer.validated_data.get("search"),
        )
        return get_paginated_response(
            request=request,
            view=self,
            items=datasets,
            serializer_class=DatasetListSerializer,
        )


class DatasetUploadAPIView(APIView):
    """Upload a dataset file and create a processing record."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Datasets"],
        request=DatasetUploadSerializer,
        responses={
            202: DatasetUploadSerializer,
            400: OpenApiResponse(description="Invalid upload request."),
            401: OpenApiResponse(description="Authentication required."),
        },
        description="Upload a CSV dataset and enqueue asynchronous processing.",
    )
    def post(self, request: Request) -> Response:
        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset = create_dataset_upload(
            owner=request.user,
            uploaded_file=serializer.validated_data["file"],
        )

        response_serializer = DatasetUploadSerializer(dataset)
        return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)


class DatasetStatusAPIView(APIView):
    """Return processing status for one dataset owned by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Datasets"],
        responses={
            200: DatasetStatusSerializer,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Dataset not found."),
        },
        description="Return processing status for one dataset owned by the current user.",
    )
    def get(self, request: Request, dataset_id: str) -> Response:
        dataset = get_dataset_for_user(
            dataset_id=dataset_id,
            owner=request.user,
        )
        serializer = DatasetStatusSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DatasetRowErrorsAPIView(APIView):
    """Return invalid row details for one dataset owned by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Datasets"],
        responses={
            200: DatasetRowErrorSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Dataset not found."),
        },
        description="Return paginated invalid row details for a dataset.",
    )
    def get(self, request: Request, dataset_id: str) -> Response:
        dataset = get_dataset_for_user(
            dataset_id=dataset_id,
            owner=request.user,
        )
        row_errors = list_dataset_row_errors(dataset_id=str(dataset.id))
        return get_paginated_response(
            request=request,
            view=self,
            items=row_errors,
            serializer_class=DatasetRowErrorSerializer,
        )


class DatasetRecordsAPIView(APIView):
    """Return valid parsed records for one dataset owned by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Datasets"],
        parameters=[
            OpenApiParameter(
                name="customer_email",
                description="Filter records by exact customer email.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="purchased_at_from",
                description="Filter records purchased on or after this date.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="purchased_at_to",
                description="Filter records purchased on or before this date.",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: DatasetRecordSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Dataset not found."),
        },
        description="Return paginated valid records for a dataset.",
    )
    def get(self, request: Request, dataset_id: str) -> Response:
        filter_serializer = DatasetRecordFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        dataset = get_dataset_for_user(
            dataset_id=dataset_id,
            owner=request.user,
        )
        records = list_dataset_records(
            dataset=dataset,
            customer_email=filter_serializer.validated_data.get("customer_email"),
            purchased_at_from=filter_serializer.validated_data.get("purchased_at_from"),
            purchased_at_to=filter_serializer.validated_data.get("purchased_at_to"),
        )
        return get_paginated_response(
            request=request,
            view=self,
            items=records,
            serializer_class=DatasetRecordSerializer,
        )


class DatasetRetryAPIView(APIView):
    """Retry processing for a pending or failed dataset."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Datasets"],
        request=None,
        responses={
            202: DatasetStatusSerializer,
            400: OpenApiResponse(description="Dataset cannot be retried."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Dataset not found."),
        },
        description="Retry processing for a pending or failed dataset.",
    )
    def post(self, request: Request, dataset_id: str) -> Response:
        dataset = get_dataset_for_user(
            dataset_id=dataset_id,
            owner=request.user,
        )

        try:
            retried_dataset = retry_dataset_processing(dataset=dataset)
        except ValueError as exc:
            return Response(
                {
                    "error": {
                        "code": 400,
                        "message": str(exc),
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DatasetStatusSerializer(retried_dataset)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class DatasetExportAPIView(APIView):
    """Export dataset summary, valid records, and invalid rows as an Excel file."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Datasets"],
        responses={
            200: OpenApiResponse(description="Excel workbook download."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Dataset not found."),
        },
        description="Download an Excel report containing summary, valid records, and invalid rows.",
    )
    def get(self, request: Request, dataset_id: str) -> FileResponse:
        dataset = get_dataset_for_user(
            dataset_id=dataset_id,
            owner=request.user,
        )
        workbook = build_dataset_export_workbook(dataset=dataset)

        return FileResponse(
            workbook,
            as_attachment=True,
            filename=f"dataset-{dataset.id}-report.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
