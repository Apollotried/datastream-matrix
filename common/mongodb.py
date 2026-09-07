from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from pymongo import MongoClient
from pymongo.database import Database


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    """Return a cached MongoDB client for the current process."""
    return MongoClient(settings.MONGODB_URI)


def get_mongo_database() -> Database:
    """Return the configured MongoDB database."""
    client = get_mongo_client()
    return client[settings.MONGODB_DATABASE]