            """FastAPI application entry-point — InsureOS backend."""

            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            from backend.routers.auth import router as auth_router
from backend.routers.policy import router as policy_router
from backend.routers.claims import router as claims_router
from backend.routers.user import router as user_router
from backend.routers.notification import router as notification_router
from backend.routers.document import router as document_router

            app = FastAPI(
                title="InsureOS API",
                version="0.1.0",
                docs_url="/api/docs",
                redoc_url="/api/redoc",
            )

            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # tighten per environment
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            app.include_router(auth_router, prefix="/api/v1/auths", tags=["Auth Service"])
app.include_router(policy_router, prefix="/api/v1/policys", tags=["Policy Service"])
app.include_router(claims_router, prefix="/api/v1/claimss", tags=["Claims Service"])
app.include_router(user_router, prefix="/api/v1/users", tags=["User Service"])
app.include_router(notification_router, prefix="/api/v1/notifications", tags=["Notification Service"])
app.include_router(document_router, prefix="/api/v1/documents", tags=["Document Service"])


            @app.get("/health")
            async def health_check() -> dict[str, str]:
                return {"status": "healthy"}


            @app.get("/ready")
            async def readiness_check() -> dict[str, str]:
                return {"status": "ready"}
