
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI

from contextdrop.config import settings
from contextdrop.database.connection import (
    init_database,
    close_database,
)
from contextdrop.storage.factory import create_storage
from contextdrop.api.routes.files import router as files_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Initialize SQLite tables
    await init_database()

    # Create storage backend
    storage = create_storage()

    # Initialize MinIO bucket
    await asyncio.to_thread(storage.initialize)

    app.state.storage = storage

    print("contextdrop started successfully")

    yield

    # Close database connection pool
    await close_database()

    print("contextdrop stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(files_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
    }
