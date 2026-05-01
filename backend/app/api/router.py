from fastapi import APIRouter
from app.api.endpoints import assessments, jobs, precommit_review

api_router = APIRouter()

api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
api_router.include_router(precommit_review.router, prefix="/precommit-review", tags=["precommit-review"])
