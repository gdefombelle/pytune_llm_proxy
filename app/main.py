import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pathlib import Path as FilePath  # alias pour éviter les conflits
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
import toml
#routers
from app import chat_router, completion_router, vision_router
from pytune_auth_common.services.rate_middleware import RateLimitMiddleware, RateLimitConfig
from simple_logger.logger import get_logger, SimpleLogger
from pytune_configuration.sync_config_singleton import config, SimpleConfig


if config is None:
    config = SimpleConfig()

logger : SimpleLogger = get_logger("llm")

# Charger les métadonnées depuis pyproject.toml
pyproject_path = FilePath(__file__).resolve().parent.parent / "pyproject.toml"
pyproject_data = toml.load(pyproject_path)
project_metadata = pyproject_data.get("project", {})

PROJECT_TITLE = project_metadata.get("name", "Unknown Service")
PROJECT_VERSION = project_metadata.get("version", "0.0.0")
PROJECT_DESCRIPTION = project_metadata.get("description", "")


### START USER SERVICE ####


logger.info(f"STARTING {PROJECT_TITLE} {PROJECT_VERSION}")


# Créer une instance de RateLimitConfig avec la config
try:
    rate_limit_config = RateLimitConfig(
        rate_limit=int(config.RATE_MIDDLEWARE_RATE_LIMIT),
        time_window=int(config.RATE_MIDDLEWARE_TIME_WINDOW),
        block_time=int(config.RATE_MIDDLEWARE_LOCK_TIME),
    )
    logger.info("pytune_fastapi rate middleware ready")
except Exception as e:
    logger.critical("Failed to set RateLimit", error=e)
    raise RuntimeError("Failed to set RateLimit:", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await logger.ainfo("LLM PROXY READY")
        
        yield  # Exécution de l'application

    except asyncio.CancelledError:
        await logger.acritical("Lifespan context was cancelled")
        raise
    finally:
        await logger.ainfo("The FastAPI PyTune LLM Proxy process finished without errors.")

# Créer l'application FastAPI avec le contexte lifespan
app = FastAPI(
    title=PROJECT_TITLE,
    version=PROJECT_VERSION,
    description=PROJECT_DESCRIPTION,
    lifespan=lifespan,
)

allowed_origins = config.ALLOWED_CORS_ORIGINS
logger.info(f"allowed_origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "X-Refresh-Token",
        "Content-Type",
        "Accept",
        "Origin",
        "Cache-Control",
    ],
    expose_headers=[
        "Authorization",
        "X-Refresh-Token",
    ],
)

try:
    app.add_middleware(
        RateLimitMiddleware,
        config=rate_limit_config,
    )
except Exception as e:
    logger.acritical("Erreur lors de l'application des middlewares", error=e)
    raise RuntimeError("Failed to load middlewares") from e

# Inclusion des routeurs
app.include_router(chat_router.router, prefix="/llm", tags=["chat"])
app.include_router(completion_router.router, prefix="/llm", tags=["completion"])
app.include_router(vision_router.router, prefix="/llm", tags=["vision"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),  # Affiche les erreurs de validation
            "body": exc.body,        # Affiche le payload brut
        },
    )


# Définir le chemin du dossier statique
static_dir = FilePath(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def health_check():
    return {"status": "ok", "service": PROJECT_TITLE, "version": PROJECT_VERSION}


