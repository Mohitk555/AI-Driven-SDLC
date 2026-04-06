"""Backend API entrypoint for the Insurance Management Platform."""

from fastapi import FastAPI

from backend.database import Base, engine
from backend.routers.auth_router import router as auth_router
from backend.routers.claims_router import router as claims_router
from backend.routers.quotes_router import router as quotes_router
from backend.routers.policies_router import router as policies_router
from backend.routers.admin_policies_router import router as admin_policies_router

app = FastAPI(
    title="Insurance Management Backend",
    version="1.0.0",
    description="Backend API for authentication and claims workflows.",
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize database schema on service startup."""
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """Service health endpoint."""
    return {"status": "ok", "service": "backend"}


app.include_router(auth_router)
app.include_router(claims_router)
app.include_router(quotes_router)
app.include_router(policies_router)
app.include_router(admin_policies_router)
