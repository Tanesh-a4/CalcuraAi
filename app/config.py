"""Simplified configuration for AI-powered amount detection."""

import os

class Settings:
    """Streamlined application settings."""
    
    # Gemini AI Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDtcY84-Lge2i2H8x5CtPSLEBT7lpm1Q9g")
    GEMINI_MODEL = "gemini-2.5-flash"
    GEMINI_TEMPERATURE = 0.1
    GEMINI_MAX_TOKENS = 2000
    
    # Basic Configuration
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")
    MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.5"))
    
    # Medical amount ranges for validation
    MIN_AMOUNT = 1.0
    MAX_AMOUNT = 99999.0

# Global settings instance  
settings = Settings()
