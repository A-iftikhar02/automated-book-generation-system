import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import books, publishing, qa, system
from .config import settings
from .services.generation import GenerationError
from .services.jobs import JobConflict, worker_loop
from .services.llm import LLMError
from .services.publishing.service import PublishingError
from .services.qa.fixes import FixError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = threading.Event()
    if settings.RUN_WORKER_IN_PROCESS:
        threading.Thread(target=worker_loop, args=(stop,), daemon=True, name="worker").start()
    yield
    stop.set()


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    version=settings.VERSION,
    description="AI book generation with human review, quality assurance and store-ready exports.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (system.router, books.router, qa.router, publishing.router):
    app.include_router(router, prefix="/api")


def _error(status: int):
    async def handle(request: Request, exc: Exception):
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    return handle


app.add_exception_handler(JobConflict, _error(409))
app.add_exception_handler(GenerationError, _error(400))
app.add_exception_handler(PublishingError, _error(400))
app.add_exception_handler(FixError, _error(409))
app.add_exception_handler(LLMError, _error(502))


@app.get("/")
def root():
    return {"name": settings.PROJECT_NAME, "version": settings.VERSION, "docs": "/docs"}
