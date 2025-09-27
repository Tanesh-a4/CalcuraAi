"""Simplified FastAPI application for AI-powered Amount Detection."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import main router
from app.routers.main_router import router

# Create FastAPI app
app = FastAPI(
    title="AI-Powered Amount Detector",
    description="Extract monetary amounts from medical documents using AI (text or images)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main router
app.include_router(router)

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "AI-Powered Amount Detector",
        "version": "2.0.0",
        "description": "Extract amounts from medical documents using Gemini AI",
        "endpoints": {
            "Image Upload": "/api/v1/extract-from-image",
            "Text Analysis": "/api/v1/extract-from-text"
        },
        "docs": "/docs",
        "features": [
            "AI-powered OCR and text analysis",
            "Medical document context understanding",
            "Multi-currency support",
            "Confidence scoring",
            "Amount type classification"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ai-amount-detector", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
