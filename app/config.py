"""Configuración de la aplicación, leída desde variables de entorno."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tienda"
    db_user: str = "tienda"
    db_password: str = "tienda"
    pool_min_size: int = 2
    pool_max_size: int = 10
    pool_timeout: float = 10.0
    default_page_size: int = 20
    max_page_size: int = 100

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            db_host=env("DB_HOST", cls.db_host),
            db_port=int(env("DB_PORT", cls.db_port)),
            db_name=env("DB_NAME", cls.db_name),
            db_user=env("DB_USER", cls.db_user),
            db_password=env("DB_PASSWORD", cls.db_password),
            pool_min_size=int(env("POOL_MIN_SIZE", cls.pool_min_size)),
            pool_max_size=int(env("POOL_MAX_SIZE", cls.pool_max_size)),
            pool_timeout=float(env("POOL_TIMEOUT", cls.pool_timeout)),
            default_page_size=int(env("DEFAULT_PAGE_SIZE", cls.default_page_size)),
            max_page_size=int(env("MAX_PAGE_SIZE", cls.max_page_size)),
        )
