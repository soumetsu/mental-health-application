from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import database_path
from app.controllers.database import DataAccessError, initialize_database
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(database_path())
    yield


app = FastAPI(
    title="Mindful Moments API",
    description="A non-diagnostic reflection and event-journaling prototype.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)


@app.exception_handler(DataAccessError)
async def data_error(_: Request, __: DataAccessError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Local data is temporarily unavailable"})

