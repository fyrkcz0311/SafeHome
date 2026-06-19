"""Configuracion del motor SQLite y utilidades de sesion."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# check_same_thread=False permite usar la conexion SQLite desde varios hilos
# (necesario con uvicorn/threadpool).
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Crea las tablas si no existen."""
    import app.models  # noqa: F401  (asegura que los modelos esten registrados)

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesion por request."""
    with Session(engine) as session:
        yield session
