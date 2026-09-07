from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from common.mongodb import get_mongo_database


DATASET_ROW_ERRORS_COLLECTION = "dataset_row_errors"


def log_dataset_row_error(
    *,
    dataset_id: str,
    row_number: int,
    raw_data: dict[str, Any],
    errors: list[str],
) -> None:
    """Persist invalid dataset row details in MongoDB."""
    db = get_mongo_database()
    db[DATASET_ROW_ERRORS_COLLECTION].insert_one(
        {
            "dataset_id": dataset_id,
            "row_number": row_number,
            "raw_data": raw_data,
            "errors": errors,
            "created_at": datetime.now(UTC),
        }
    )