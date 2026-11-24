"""MongoDB client with xdist-safe instance wiring.

Port of ``src/library/mongo_db.py`` + config from
``src/services/db/mongo-db-service.resource``.

Replaces module-level ``_client`` / ``_db`` globals with an instance-owned
client. Wired via the ``mongo_client`` fixture so pytest-xdist is safe.

Return shape matches Robot keywords::

    {"status_code": 0 | 1, "body": ...}

Surface: ``find_one``, ``update_one``, ``delete_one``, ``delete_many``,
``insert_one`` (seed/cleanup for promissory and similar domains).
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote_plus

from bson import ObjectId
from pymongo import MongoClient as PyMongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from tests.config.settings import Settings

Query = Mapping[str, Any] | str | list[Any] | None
Sort = Sequence[Any] | None

# Replica hostnames do not resolve on laptops; map to cluster IPs.
_REPLICA_MEMBER_HOSTS = {
    "stage-mongodb-server-1": "10.198.111.51",
    "stage-mongodb-server-3": "10.198.111.53",
}


def _writable_host_from_hello(hello: Mapping[str, Any], current_host: str) -> str | None:
    """Return the IP of the replica primary when ``current_host`` is not writable."""
    if hello.get("isWritablePrimary") or hello.get("ismaster"):
        return None
    primary = str(hello.get("primary") or "")
    member = primary.split(":", 1)[0].strip()
    if not member:
        return None
    mapped = _REPLICA_MEMBER_HOSTS.get(member)
    if mapped is None or mapped == current_host:
        return None
    return mapped


def _prepare(data: Any) -> Any:
    """Accept dict/list, JSON string, or Python-literal string (Robot parity)."""
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(data)
            except Exception as exc:
                raise ValueError(f"Could not parse string input as dict or list: {data}") from exc
    if data is None:
        return {}
    raise TypeError(f"Unsupported type for MongoDB input: {type(data)}")


def _stringify_id(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {}
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
    return doc


class MongoDbClient:
    """Context-manager Mongo client.

    Prefer::

        with MongoDbClient(settings) as db:
            result = db.find_one("purchase_management_db", "purchases", {"ticket": t})
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: PyMongoClient[Any] | None = None
        self._db: Database[Any] | None = None
        self._db_name: str | None = None

    def __enter__(self) -> MongoDbClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying PyMongo client if open."""
        if self._client is not None:
            try:
                self._client.close()
            except PyMongoError:
                pass
            finally:
                self._client = None
                self._db = None
                self._db_name = None

    def build_config(self, db_name: str) -> dict[str, Any]:
        """Port of ``Build Config For Mongo Db Handler``.

        Username defaults to ``{db_name with _db → _user}``. Known env overrides
        (credit / digital-signature / …) are applied when present in Settings.
        """
        user = db_name.replace("_db", "_user")
        overrides = {
            "switch_credit_db": getattr(self._settings, "credit_user", "") or None,
            "digital_signature_provider_db": getattr(self._settings, "digital_signature_user", "")
            or None,
            "credit_score_db": getattr(self._settings, "score_user", "") or None,
            "underwriting_db": getattr(self._settings, "underwriting_user", "") or None,
            "app_subscription_db": getattr(self._settings, "app_subscription_user", "") or None,
        }
        override_user = overrides.get(db_name)
        if override_user:
            user = override_user

        return {
            "user": user,
            "password": self._settings.mongo_db_default_pass,
            "host": self._settings.mongo_db_default_host,
            "port": int(self._settings.mongo_db_default_port),
            "db_name": db_name,
        }

    def connect(self, db_name: str) -> None:
        """Open a connection to ``db_name``. Closes any previous connection first.

        Uses ``directConnection=true``. If the host is a secondary, reconnects to
        the mapped primary so writes do not fail with ``NotWritablePrimary``.
        """
        self.close()
        config = self.build_config(db_name)
        host = str(config["host"])
        try:
            self._open(db_name, config, host)
            db = self._db
            if db is None:
                raise RuntimeError("MongoDB connection was not opened")
            hello = db.command("hello")
            primary_host = _writable_host_from_hello(hello, host)
            if primary_host is not None:
                self.close()
                self._open(db_name, config, primary_host)
        except PyMongoError as exc:
            self.close()
            raise RuntimeError(f"Error connecting to MongoDB: {exc}") from exc

    def _open(self, db_name: str, config: Mapping[str, Any], host: str) -> None:
        """Open a direct connection to ``host`` for ``db_name``."""
        user = quote_plus(str(config["user"]))
        password = quote_plus(str(config["password"]))
        port = int(config["port"])
        uri = (
            f"mongodb://{user}:{password}@{host}:{port}/{db_name}"
            f"?authSource={db_name}"
            "&authMechanism=SCRAM-SHA-1"
            "&connectTimeoutMS=20000"
            "&serverSelectionTimeoutMS=20000"
            "&directConnection=true"
        )
        self._client = PyMongoClient(uri)
        self._db = self._client[db_name]
        self._db_name = db_name

    def _collection(self, collection_name: str) -> Any:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db[collection_name]

    def _with_db(self, db_name: str, fn: Any) -> dict[str, Any]:
        try:
            self.connect(db_name)
            return fn()
        except (PyMongoError, ValueError, TypeError, RuntimeError) as exc:
            return {"status_code": 1, "body": {"error": str(exc)}}
        finally:
            self.close()

    def find_one(
        self,
        db_name: str,
        collection_name: str,
        query: Query = None,
        sort: Sort = None,
        projection: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Port of Mongo Db Find One.

        Args:
            db_name: Mongo database name.
            collection_name: Collection to query.
            query: Filter document (dict, JSON string, or Python literal).
            sort: Optional sort specification for ``find_one``.
            projection: Optional field filter (include keys with ``1``).

        Returns:
            ``{status_code, body}`` envelope (status 0 on success).
        """

        def _run() -> dict[str, Any]:
            prepared = _prepare(query or {})
            kwargs: dict[str, Any] = {}
            if projection is not None:
                kwargs["projection"] = dict(projection)
            if sort is not None:
                kwargs["sort"] = sort
            doc = self._collection(collection_name).find_one(prepared, **kwargs)
            return {"status_code": 0, "body": _stringify_id(dict(doc) if doc else {})}

        return self._with_db(db_name, _run)

    def update_one(
        self,
        db_name: str,
        collection_name: str,
        filter_query: Any,
        update: Any,
    ) -> dict[str, Any]:
        """Update a single document (e.g. soft-delete / status flip in cleanup).

        Args:
            db_name: Mongo database name.
            collection_name: Collection to mutate.
            filter_query: Filter identifying the document to update.
            update: Update document (e.g. ``{"$set": {...}}``).

        Returns:
            ``{status_code, body}`` envelope with ``matched_count`` / ``modified_count``.
        """

        def _run() -> dict[str, Any]:
            result = self._collection(collection_name).update_one(
                _prepare(filter_query),
                _prepare(update),
            )
            return {
                "status_code": 0,
                "body": {
                    "matched_count": result.matched_count,
                    "modified_count": result.modified_count,
                },
            }

        return self._with_db(db_name, _run)

    def count_documents(
        self, db_name: str, collection_name: str, filter_query: Any = None
    ) -> dict[str, Any]:
        """Count documents matching ``filter_query``.

        Returns:
            ``{status_code, body}`` with ``count``.
        """

        def _run() -> dict[str, Any]:
            count = self._collection(collection_name).count_documents(_prepare(filter_query or {}))
            return {"status_code": 0, "body": {"count": count}}

        return self._with_db(db_name, _run)

    def delete_one(self, db_name: str, collection_name: str, filter_query: Any) -> dict[str, Any]:
        """Port of Mongo Db Delete One — used for mock-terminal teardown.

        Args:
            db_name: Mongo database name.
            collection_name: Collection to mutate.
            filter_query: Filter identifying the document to delete.

        Returns:
            ``{status_code, body}`` envelope with ``deleted_count``.
        """

        def _run() -> dict[str, Any]:
            result = self._collection(collection_name).delete_one(_prepare(filter_query))
            return {
                "status_code": 0,
                "body": {"deleted_count": result.deleted_count},
            }

        return self._with_db(db_name, _run)

    def delete_many(self, db_name: str, collection_name: str, filter_query: Any) -> dict[str, Any]:
        """Delete all documents matching ``filter_query``.

        Args:
            db_name: Mongo database name.
            collection_name: Collection to mutate.
            filter_query: Filter identifying documents to delete.

        Returns:
            ``{status_code, body}`` envelope with ``deleted_count``.
        """

        def _run() -> dict[str, Any]:
            result = self._collection(collection_name).delete_many(_prepare(filter_query))
            return {
                "status_code": 0,
                "body": {"deleted_count": result.deleted_count},
            }

        return self._with_db(db_name, _run)

    def insert_one(self, db_name: str, collection_name: str, document: Any) -> dict[str, Any]:
        """Insert a single document (e.g. promissory-note seed clone).

        Args:
            db_name: Mongo database name.
            collection_name: Collection to mutate.
            document: Document to insert.

        Returns:
            ``{status_code, body}`` envelope with inserted ``_id`` as string.
        """

        def _run() -> dict[str, Any]:
            result = self._collection(collection_name).insert_one(_prepare(document))
            return {
                "status_code": 0,
                "body": {"inserted_id": str(result.inserted_id)},
            }

        return self._with_db(db_name, _run)
