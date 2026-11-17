import hashlib
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def session_run_id():
    """Identidad compartida por los workers de una misma ejecución/despliegue."""
    if os.getenv("RAILWAY_DEPLOYMENT_ID"):
        return hashlib.sha256(
            ("railway:" + os.environ["RAILWAY_DEPLOYMENT_ID"]).encode()
        ).hexdigest()
    return os.getenv("_VETCARE_SESSION_RUN_ID") or secrets.token_hex(32)


@dataclass
class Config:
    root: Path = ROOT
    database: str = ""
    production: bool = False
    secret: str = ""
    media: Path = ROOT / "media"
    pool_size: int = 8
    session_hours: int = 8
    testing: bool = False
    session_run_id: str = field(default_factory=session_run_id)

    @classmethod
    def load(cls, database=None, testing=False):
        load_dotenv(ROOT / ".env", override=False, interpolate=False)
        missing = [
            n
            for n in [
                "MYSQLHOST",
                "MYSQLPORT",
                "MYSQLDATABASE",
                "MYSQLUSER",
                "MYSQLPASSWORD",
            ]
            if not os.getenv(n)
        ]
        secret = os.getenv("VETCARE_SECRET_KEY", "")
        if missing or len(secret) < 32:
            raise RuntimeError(
                "Configura "
                + ", ".join(missing or ["VETCARE_SECRET_KEY (mínimo 32 caracteres)"])
                + " en el entorno o .env."
            )
        production = os.getenv("VETCARE_PRODUCTION", "false").lower() == "true"
        media = Path(os.getenv("MEDIA_ROOT") or ROOT / "media")
        if (
            production
            and os.getenv("VETCARE_SERVICE", "web") != "worker"
            and not os.getenv("MEDIA_ROOT")
        ):
            raise RuntimeError(
                "Producción requiere MEDIA_ROOT en un volumen persistente."
            )
        name = database or os.environ["MYSQLDATABASE"]
        if testing and (
            not name.startswith("test_vetcare_") or name == os.environ["MYSQLDATABASE"]
        ):
            raise RuntimeError("Las pruebas requieren una base aislada test_vetcare_.")
        return cls(
            database=name,
            secret=secret,
            production=production,
            media=media,
            pool_size=int(os.getenv("DB_POOL_SIZE", "8")),
            testing=testing,
        )

    @property
    def hosts(self):
        hosts = set(
            os.getenv("VETCARE_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
        )
        hosts.update(
            filter(
                None, [os.getenv("RAILWAY_PUBLIC_DOMAIN"), "healthcheck.railway.app"]
            )
        )
        return {h.strip() for h in hosts}
