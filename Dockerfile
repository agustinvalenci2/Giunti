# syntax=docker/dockerfile:1

# Build the React application; Node is not needed in the final image.
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
RUN npm run build

# FastAPI serves both /api and the compiled React application.
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_DEBUG=false \
    DATABASE_PATH=/data/app.sqlite3 \
    MEDIA_ROOT=/data/media
WORKDIR /app

COPY requirements.txt requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-lock.txt

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data/media \
    && chown -R app:app /data

COPY alembic.ini ./
COPY backend ./backend
COPY migrations ./migrations
COPY scripts/__init__.py scripts/start_container.py ./scripts/
COPY --from=frontend-build /frontend/dist ./frontend/dist

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os; from urllib.request import urlopen; base = 'http://127.0.0.1:' + os.environ.get('PORT', '8000'); urlopen(base + '/api/health', timeout=3).close(); urlopen(base + '/', timeout=3).close()"]

ENTRYPOINT ["python", "-m", "scripts.start_container"]
# Let the entrypoint choose the server command using the runtime PORT variable.
CMD []
