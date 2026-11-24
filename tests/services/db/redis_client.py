"""Redis client — port of ``src/library/redis_db.py`` and Robot config.

Replaces the unsafe module-level ``_connection`` global with an instance-owned
client. Wired via the ``redis_client`` fixture in ``tests/conftest.py`` so
pytest-xdist workers never share state.

This step covers what ``Login To App`` needs for OTP:

    Redis Get Key    key=auth_otp_<userId>    master_name=standalone

Return shape matches the Robot keywords:

    {"status_code": 0 | 1, "body": ...}

where ``0`` means success and ``1`` means a driver/error (not an HTTP status).
``decode_responses=False`` matches the legacy library so OTP JSON arrives as
bytes and callers decode the same way Robot does.

``master_name=STANDALONE`` (the default) resolves through Redis Sentinel to
the ``redis-new-master`` master rather than connecting to a fixed host:port.
"""

from __future__ import annotations

from typing import Any

import redis
from redis.exceptions import RedisError
from redis.sentinel import Sentinel

from tests.config.settings import Settings

# Master names used by redis-db-service.resource / Login To App OTP.
# STANDALONE is sentinel-backed despite the name — kept for caller compatibility.
STANDALONE = "standalone"
SECOND_STANDALONE = "second_standalone"


class RedisClient:
    """Context-manager Redis client. Prefer::

        with RedisClient(settings) as r:
            result = r.get_key("auth_otp_<userId>")

    Each method opens a connection, runs the command, then closes — matching
    Robot's ``Initiate REDIS Db Connection`` / ``Close Connection`` pair.
    ``STANDALONE`` connects via Sentinel; cluster / TLS are not ported yet.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: redis.Redis | None = None
        self._sentinel: Sentinel | None = None

    def __enter__(self) -> RedisClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Drop the connection reference. Safe to call multiple times."""
        if self._connection is not None:
            try:
                self._connection.close()
            except RedisError:
                pass
            finally:
                self._connection = None

    def build_config(self, master_name: str = SECOND_STANDALONE) -> dict[str, Any]:
        """Port of ``Build Config For REDIS Db Handler`` — direct host:port paths.

        Only ``SECOND_STANDALONE`` connects directly; ``STANDALONE`` is
        sentinel-backed and handled separately in :meth:`connect`.
        """
        if master_name == SECOND_STANDALONE:
            host = self._settings.redis_platform_second_standalone_host
            port = self._settings.redis_platform_second_standalone_port
            if not host or not port:
                raise ValueError("second_standalone Redis host/port not configured in settings")
            return {"host": host, "port": port, "db": 0}
        raise ValueError(
            f"Redis master_name={master_name!r} has no direct host:port config; "
            f"supported: {SECOND_STANDALONE!r}"
        )

    def _sentinel_client(self) -> Sentinel:
        """Lazily build the Sentinel discovery client from the configured nodes."""
        if self._sentinel is None:
            hosts = self._settings.redis_platform_sentinel_hosts
            if not hosts:
                raise ValueError("Redis sentinel hosts not configured in settings")
            nodes: list[tuple[str, int]] = []
            for entry in hosts:
                host, _, port = entry.partition(":")
                nodes.append((host, int(port)))
            self._sentinel = Sentinel(nodes, socket_timeout=5)
        return self._sentinel

    def connect(self, master_name: str = STANDALONE) -> None:
        """Open a connection. Closes any previous connection first.

        ``STANDALONE`` resolves the current master via Sentinel; other
        master names connect directly per :meth:`build_config`.
        """
        self.close()
        try:
            if master_name == STANDALONE:
                sentinel = self._sentinel_client()
                self._connection = sentinel.master_for(
                    self._settings.redis_platform_sentinel_master_name,
                    db=0,
                    socket_timeout=5,
                    decode_responses=False,
                )
            else:
                config = self.build_config(master_name)
                self._connection = redis.Redis(
                    host=config["host"],
                    port=config["port"],
                    db=config["db"],
                    socket_timeout=5,
                    decode_responses=False,
                )
            self._connection.ping()
        except RedisError as exc:
            self._connection = None
            raise RuntimeError(f"Error connecting to Redis ({master_name}): {exc}") from exc

    def get_key(self, key: str, master_name: str = STANDALONE) -> dict[str, Any]:
        """Port of ``Redis Get Key`` — returns ``{"status_code", "body": {"value"}}``.

        ``body["value"]`` is ``bytes | None`` (legacy ``decode_responses=False``).
        """
        try:
            self.connect(master_name)
            assert self._connection is not None
            value = self._connection.get(key)
            return {"status_code": 0, "body": {"value": value}}
        except RedisError as exc:
            return {"status_code": 1, "body": {"error": str(exc)}}
        finally:
            self.close()

    def set_key(
        self,
        key: str,
        value: Any,
        master_name: str = STANDALONE,
        ex: int | None = None,
    ) -> dict[str, Any]:
        """Set a key (foundation helper; Robot had broader redis keywords)."""
        try:
            self.connect(master_name)
            assert self._connection is not None
            ok = self._connection.set(key, value, ex=ex)
            return {"status_code": 0, "body": {"ok": bool(ok)}}
        except RedisError as exc:
            return {"status_code": 1, "body": {"error": str(exc)}}
        finally:
            self.close()
