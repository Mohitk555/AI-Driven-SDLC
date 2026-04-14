"""Backend API entrypoint for the Insurance Management Platform."""

from fastapi import FastAPI

from backend.database import Base, engine
from backend.routers.auth_router import router as auth_router
from backend.routers.claims_router import router as claims_router
from backend.routers.quotes_router import router as quotes_router
from backend.routers.policies_router import router as policies_router
from backend.routers.admin_policies_router import router as admin_policies_router
from backend.routers.risk_rules_router import router as risk_rules_router
from backend.routers.claims_dashboard_router import router as claims_dashboard_router
from backend.services.rule_seeder import seed_default_rules

app = FastAPI(
    title="Insurance Management Backend",
    version="1.0.0",
    description="Backend API for authentication and claims workflows.",
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize database schema and seed default data on startup."""
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        seed_default_rules(db)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """Service health endpoint."""
    return {"status": "ok", "service": "backend"}


app.include_router(auth_router)
app.include_router(claims_router)
app.include_router(quotes_router)
app.include_router(policies_router)
app.include_router(admin_policies_router)
app.include_router(risk_rules_router)
app.include_router(claims_dashboard_router)
