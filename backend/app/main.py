"""FastAPI application entrypoint and middleware configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.api.routes import router as api_router

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Deterministic statement categorizer for Freelance Tech Consultants",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach API routes
app.include_router(api_router)


@app.get("/")
def root():
    """Service status and meta info."""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "engine": "Deterministic Heuristic Engine (No LLM runtime)",
    }
