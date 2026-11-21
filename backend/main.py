from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import auth, documents
from .config import settings


def create_app():
    app = FastAPI(title="Cuaderno API", version="2.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if (origin and origin.rstrip("/") not in settings.allowed_origins) or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Origin not allowed."}, status_code=403)
        if request.method == "POST":
            length = request.headers.get("content-length")
            if length:
                try:
                    if int(length) > settings.MAX_UPLOAD_BYTES + 1024 * 1024:
                        return JSONResponse({"detail": "The file exceeds the size limit."}, status_code=413)
                except ValueError:
                    return JSONResponse({"detail": "Invalid request size."}, status_code=400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(request, exc):
        # Avoid reflecting passwords or complete document bodies in validation errors.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(error["loc"]), "msg": error["msg"]} for error in exc.errors()
        ]})

    app.include_router(auth.router)
    app.include_router(documents.router)

    @app.get("/api/health", tags=["Status"])
    def health():
        return {"status": "ok", "framework": "FastAPI"}

    # Vite proxies /api in development. In production FastAPI serves the built SPA.
    assets = settings.frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.split("/")[0] in {"api", "assets", "media", "private-media", "admin"}:
            raise HTTPException(404, "Resource not found.")
        index = settings.frontend_dist / "index.html"
        if not index.is_file():
            raise HTTPException(503, "Build the frontend with npm run build or open Vite at http://127.0.0.1:5173.")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
