"""Postgres client — port of ``src/library/postgres_db.py`` and Robot config.

Replaces module-level ``_connection`` / ``_cursor`` globals. Wired via the
``postgres_client`` fixture for xdist safety.

Return shape matches Robot:

    {"status_code": 0 | 1, "body": ...}
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor

from tests.config.settings import Settings

Params = Sequence[Any] | dict[str, Any] | None

# Robot handler names → settings fields
_DB_HANDLERS = {
    "collateralmanagement_db": "collateral",
    "treasurymanagement": "treasury",
}


class PostgresClient:
    """Context-manager Postgres client used via ``with PostgresClient(settings) as db``."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: Any = None
        self._cursor: Any = None

    def __enter__(self) -> PostgresClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close cursor and connection if open. Safe to call multiple times."""
        try:
            if self._cursor is not None:
                self._cursor.close()
            if self._connection is not None:
                self._connection.close()
        except Error as exc:
            raise RuntimeError(f"Error closing PostgreSQL connection: {exc}") from exc
        finally:
            self._cursor = None
            self._connection = None

    def build_config(self, db_name: str) -> dict[str, Any]:
        """Port of ``Build Config For POSTGRES Db Handler``."""
        if db_name == "collateralmanagement_db":
            return {
                "user": self._settings.postgres_db_collateral_management_user,
                "password": self._settings.postgres_db_collateral_management_pass,
                "host": self._settings.postgres_db_collateral_management_host,
                "port": self._settings.postgres_db_collateral_management_port,
                "database": db_name,
            }
        if db_name == "treasurymanagement":
            return {
                "user": self._settings.postgres_db_treasury_statement_user,
                "password": self._settings.postgres_db_treasury_statement_pass,
                "host": self._settings.postgres_db_collateral_management_host,
                "port": self._settings.postgres_db_collateral_management_port,
                "database": db_name,
            }
        raise ValueError(
            f"Postgres handler not implemented for database {db_name!r}. "
            f"Supported: {', '.join(sorted(_DB_HANDLERS))}"
        )

    def connect(self, db_name: str) -> None:
        """Open a connection to ``db_name``. Closes any previous connection first."""
        self.close()
        config = self.build_config(db_name)
        try:
            self._connection = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                dbname=config["database"],
            )
            self._cursor = self._connection.cursor(cursor_factory=RealDictCursor)
        except Error as exc:
            self._connection = None
            self._cursor = None
            raise RuntimeError(f"Error connecting to PostgreSQL: {exc}") from exc

    def fetch_all(
        self,
        db_name: str,
        query: str,
        params: Params = None,
        use_transaction: bool = False,
    ) -> dict[str, Any]:
        """Port of Postgres Fetch All — SELECT returning all rows."""
        return self._run_select(db_name, query, params, use_transaction, fetch="all")

    def fetch_one(
        self,
        db_name: str,
        query: str,
        params: Params = None,
        use_transaction: bool = False,
    ) -> dict[str, Any]:
        """Port of Postgres Fetch One — SELECT returning a single row (or ``{}``)."""
        return self._run_select(db_name, query, params, use_transaction, fetch="one")

    def execute_query(
        self,
        db_name: str,
        query: str,
        params: Params = None,
        use_transaction: bool = False,
    ) -> dict[str, Any]:
        """Port of Postgres Execute Query — INSERT / UPDATE / DELETE / DDL."""
        try:
            self.connect(db_name)
            assert self._connection is not None and self._cursor is not None
            if use_transaction:
                self._connection.autocommit = False
            self._cursor.execute(query, params)
            affected = self._cursor.rowcount
            if use_transaction:
                self._connection.commit()
                self._connection.autocommit = True
            else:
                self._connection.commit()
            return {"status_code": 0, "body": {"affected_rows": affected}}
        except Error as exc:
            if self._connection is not None:
                try:
                    self._connection.rollback()
                except Error:
                    pass
            return {"status_code": 1, "body": {"error": str(exc)}}
        finally:
            self.close()

    def _run_select(
        self,
        db_name: str,
        query: str,
        params: Params,
        use_transaction: bool,
        fetch: str,
    ) -> dict[str, Any]:
        try:
            self.connect(db_name)
            assert self._connection is not None and self._cursor is not None
            if use_transaction:
                self._connection.autocommit = False
            self._cursor.execute(query, params)
            if fetch == "one":
                row = self._cursor.fetchone()
                body: Any = dict(row) if row else {}
            else:
                rows = self._cursor.fetchall()
                body = [dict(r) for r in rows]
            if use_transaction:
                self._connection.commit()
                self._connection.autocommit = True
            return {"status_code": 0, "body": body}
        except Error as exc:
            if self._connection is not None:
                try:
                    self._connection.rollback()
                except Error:
                    pass
            return {"status_code": 1, "body": {"error": str(exc)}}
        finally:
            self.close()
