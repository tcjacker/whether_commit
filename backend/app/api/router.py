from fastapi import APIRouter
from app.api.endpoints import overview, jobs, capabilities, changes, verification

api_router = APIRouter()

# Register core endpoints
api_router.include_router(overview.router, prefix="/overview", tags=["overview"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Register Phase 2 endpoints
api_router.include_router(capabilities.router, prefix="/capabilities", tags=["capabilities"])
api_router.include_router(changes.router, prefix="/changes", tags=["changes"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
