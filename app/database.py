"""Acceso a PostgreSQL mediante un pool de conexiones (psycopg 3)."""
from __future__ import annotations

from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import Settings


class Database:
    """Encapsula el pool de conexiones. Una instancia por proceso/pod."""

    def __init__(self, settings: Settings) -> None:
        conninfo = make_conninfo(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )
        self._pool = ConnectionPool(
            conninfo=conninfo,
            min_size=settings.pool_min_size,
            max_size=settings.pool_max_size,
            timeout=settings.pool_timeout,
            kwargs={"row_factory": dict_row},
            open=False,
        )

    def open(self) -> None:
        # wait=False: el pod arranca aunque la BD tarde; el pool reintenta en segundo plano.
        self._pool.open(wait=False)

    def connection(self):
        """Context manager: confirma (commit) al salir o revierte si hay excepción."""
        return self._pool.connection()

    def ping(self) -> bool:
        try:
            with self._pool.connection(timeout=2) as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._pool.close()
