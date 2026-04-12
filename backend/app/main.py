from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router

app = FastAPI(
    title="AI Application Overview API",
    description="API for the AI Application Overview MVP (Lightweight Edition)",
    version="1.0.0",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "ok"}
