"""Apply database migrations, then replace this process with the application."""
import os
import subprocess
import sys

from backend.config import settings


def main():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.media_root.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    command = sys.argv[1:] or [
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "0.0.0.0", "--port", "8000",
    ]
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
