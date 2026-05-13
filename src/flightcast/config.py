"""
Application configuration loaded from environment variables.
Supports both the Docker environment (DB_HOST=db) and local dev (.env file).
"""
import os
from dataclasses import dataclass


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    def as_connect_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "local_infile": True,
            "autocommit": False,
        }


def load_db_config() -> DBConfig:
    return DBConfig(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "flightcast"),
        password=os.environ.get("DB_PASSWORD", "flightcastpw"),
        database=os.environ.get("DB_NAME", "flightcast"),
    )


MODEL_VERSION_DEFAULT = "lgbm-v2.1"
CONFIDENCE_LEVEL = 0.90
HORIZON_DAYS = 30
N_ROUTES = 50
N_DAYS = 730
GLOBAL_SEED = 42
START_DATE = "2019-01-01"
