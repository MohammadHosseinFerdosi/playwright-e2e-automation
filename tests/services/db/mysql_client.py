"""MySQL client — port of ``src/library/mysql_db.py`` and Robot config.

Replaces the unsafe module-level ``_connection`` / ``_cursor`` globals with an
instance-owned connection. Wired via the ``mysql_client`` fixture in
``tests/conftest.py`` so pytest-xdist workers never share state.

Return shape matches the Robot keywords (``MySQL Fetch All`` / ``Fetch One`` /
``Execute Query``):

    {"status_code": 0 | 1, "body": ...}

where ``0`` means success and ``1`` means a driver/query error (this is *not*
an HTTP status code).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import mysql.connector
from mysql.connector import Error

from tests.config.settings import Settings

Params = Sequence[Any] | dict[str, Any] | None


class MySQLClient:
    """Context-manager MySQL client. Prefer::

        with MySQLClient(settings) as db:
            result = db.fetch_all("user_db", "SELECT ...")

    Each query method opens a connection for the requested ``db_name``, runs
    the statement, then closes — matching Robot's
    ``Initiate MySQL Db Connection`` / ``Close Db Connection`` pair per call.
    The instance still owns the connection fields so nothing lives at module
    scope.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: Any = None
        self._cursor: Any = None

    def __enter__(self) -> MySQLClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close cursor and connection if open. Safe to call multiple times."""
        try:
            if self._cursor is not None:
                self._cursor.close()
            if self._connection is not None and self._connection.is_connected():
                self._connection.close()
        except Error as exc:
            raise RuntimeError(f"Error closing MySQL connection: {exc}") from exc
        finally:
            self._cursor = None
            self._connection = None

    def build_config(self, db_name: str) -> dict[str, Any]:
        """Port of ``Build Config For MYSQL Db Handler``.

        Username is derived as ``{db_name with _db → _user}`` (e.g. ``user_db``
        → ``user_user``). Host/password default to ``MYSQL_DB_DEFAULT_*`` with
        overrides for ``wallet_provider_db`` and ``general_ledger_db``.
        """
        user = db_name.replace("_db", "_user")
        host = self._settings.mysql_db_default_host
        port = self._settings.mysql_db_default_port
        password = CHANGE_ME

        if db_name == "wallet_provider_db":
            password = CHANGE_ME
            host = self._settings.wallet_provider_mysql_db_host
        elif db_name == "general_ledger_db":
            password = CHANGE_ME
            host = self._settings.general_ledger_mysql_db_host

        return {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": db_name,
        }

    def connect(self, db_name: str) -> None:
        """Open a connection to ``db_name``. Closes any previous connection first."""
        self.close()
        config = self.build_config(db_name)
        try:
            self._connection = mysql.connector.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["database"],
            )
            self._cursor = self._connection.cursor(dictionary=True)
        except Error as exc:
            self._connection = None
            self._cursor = None
            raise RuntimeError(f"Error connecting to MySQL: {exc}") from exc

    def fetch_all(
        self,
        db_name: str,
        query: str,
        params: Params = None,
        use_transaction: bool = True,
    ) -> dict[str, Any]:
        """Port of ``MySQL Fetch All`` — SELECT returning all rows."""
        return self._run_select(db_name, query, params, use_transaction, fetch="all")

    def fetch_one(
        self,
        db_name: str,
        query: str,
        params: Params = None,
        use_transaction: bool = True,
    ) -> dict[str, Any]:
        """Port of ``MySQL Fetch One`` — SELECT returning a single row (or ``{}``)."""
        return self._run_select(db_name, query, params, use_transaction, fetch="one")

    def execute_query(
        self,
        db_name: str,
        query: str,
        params: Params = None,
        use_transaction: bool = True,
    ) -> dict[str, Any]:
        """Port of ``MySQL Execute Query`` — INSERT / UPDATE / DELETE / DDL."""
        try:
            self.connect(db_name)
            assert self._connection is not None and self._cursor is not None
            if use_transaction:
                self._connection.start_transaction()
            self._cursor.execute(query, params)
            affected_rows = self._cursor.rowcount
            if use_transaction:
                self._connection.commit()
            return {"status_code": 0, "body": {"affected_rows": affected_rows}}
        except Error as exc:
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
                self._connection.start_transaction()
            self._cursor.execute(query, params)
            if fetch == "one":
                row = self._cursor.fetchone()
                body: Any = row or {}
            else:
                body = self._cursor.fetchall()
            if use_transaction:
                self._connection.commit()
            return {"status_code": 0, "body": body}
        except Error as exc:
            return {"status_code": 1, "body": {"error": str(exc)}}
        finally:
            self.close()
