"""Punto de entrada de la API SafeHome Kitchen Monitor."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import alertas, dashboard_ws, dispositivos, lecturas, telemetria

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetria.router)
app.include_router(dispositivos.router)
app.include_router(lecturas.router)
app.include_router(alertas.router)
app.include_router(dashboard_ws.router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["health"])
def root():
    return {
        "app": settings.app_name,
        "estado": "ok",
        "docs": "/docs",
        "dashboard": "/static/dashboard.html",
    }
