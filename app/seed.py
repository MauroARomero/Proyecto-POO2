"""Crea el esquema y carga los datos de prueba (idempotente).

Uso:  python -m app.seed
Variables: DB_* (como la API) y SEED_FORCE=true para volver a sembrar aunque ya haya datos.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo

from .config import Settings

DB_DIR = Path(__file__).resolve().parents[1] / "db"


def connect_with_retry(settings: Settings, attempts: int = 60, delay: float = 2.0):
    conninfo = make_conninfo(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    for attempt in range(1, attempts + 1):
        try:
            return psycopg.connect(conninfo, autocommit=True)
        except psycopg.OperationalError as exc:
            print(f"[seed] BD no disponible (intento {attempt}/{attempts}): {exc}", flush=True)
            time.sleep(delay)
    sys.exit("[seed] No fue posible conectar a la base de datos")


def main() -> None:
    settings = Settings.from_env()
    force = os.environ.get("SEED_FORCE", "false").lower() == "true"
    with connect_with_retry(settings) as conn:
        # Sin parámetros, psycopg permite enviar varias sentencias en un solo execute().
        conn.execute((DB_DIR / "schema.sql").read_text(encoding="utf-8"))
        existing = conn.execute("SELECT count(*) FROM products").fetchone()[0]
        if existing > 0 and not force:
            print(f"[seed] Ya hay {existing} productos; no se vuelve a sembrar.", flush=True)
        else:
            started = time.perf_counter()
            conn.execute((DB_DIR / "seed.sql").read_text(encoding="utf-8"))
            print(f"[seed] Datos cargados en {time.perf_counter() - started:.1f} s", flush=True)

        for table in ("categories", "products", "customers", "orders", "order_items"):
            n = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"[seed] {table:12s} {n:>8d} registros", flush=True)


if __name__ == "__main__":
    main()
