import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def allowed_origins_from_environment():
    configured = os.getenv(
        "APP_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5173,http://localhost:5173",
    )
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    # Trust deployment configuration, never request Host / X-Forwarded-Host headers.
    # Vercel supplies these project-specific hostnames without the HTTPS scheme.
    for name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        hostname = os.getenv(name, "").strip().rstrip("/").lower()
        if hostname:
            origins.append(f"https://{hostname}")
    return list(dict.fromkeys(origins))


@dataclass
class Settings:
    debug: bool = field(default_factory=lambda: os.getenv("APP_DEBUG", "true").lower() == "true")
    database_path: Path = field(default_factory=lambda: Path(os.getenv("DATABASE_PATH", str(ROOT / "app.sqlite3"))).resolve())
    media_root: Path = field(default_factory=lambda: Path(os.getenv("MEDIA_ROOT", str(ROOT / "media"))).resolve())
    frontend_dist: Path = field(default_factory=lambda: ROOT / "frontend" / "dist")
    allowed_origins: list[str] = field(default_factory=allowed_origins_from_environment)
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
    GEMINI_TIMEOUT_SECONDS: int = field(default_factory=lambda: max(1, min(int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90")), 120)))
    MAX_UPLOAD_BYTES: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024)
    MAX_EXTRACTED_CHARACTERS: int = 150_000
    MAX_PDF_PAGES: int = 100
    session_days: int = 7

    @property
    def database_url(self):
        return f"sqlite:///{self.database_path.as_posix()}"


settings = Settings()
