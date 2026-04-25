from fastapi import APIRouter
from app.api.endpoints import assessments, jobs

api_router = APIRouter()

api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
