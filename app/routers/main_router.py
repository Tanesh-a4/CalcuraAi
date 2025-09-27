"""4-step pipeline router for amount extraction."""

import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from app.models.schemas import TextInput, FinalPipelineOutput
from app.services.ai_service import four_step_extractor

router = APIRouter(prefix="/api/v1", tags=["Amount Extraction"])


@router.post("/extract-from-image", response_model=FinalPipelineOutput)
async def extract_from_image(
    file: UploadFile = File(...)
) -> FinalPipelineOutput:
    """Extract amounts from uploaded image using AI pipeline."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Process with 4-step pipeline
        result = four_step_extractor.extract_from_image(image_data)
        
        return result
    
    except Exception as e:
        # Return error in pipeline format
        from app.models.schemas import OCROutput, NormalizationOutput, ClassificationOutput
        
        return FinalPipelineOutput(
            currency=None,
            amounts=[],
            status="error",
            reason=f"Request processing failed: {str(e)}",
            ocr_step=OCROutput(raw_tokens=[], confidence=0.0, status="no_amounts_found"),
            normalization_step=NormalizationOutput(normalized_amounts=[], normalization_confidence=0.0),
            classification_step=ClassificationOutput(amounts=[], confidence=0.0)
        )


@router.post("/extract-from-text", response_model=FinalPipelineOutput)
async def extract_from_text(input_data: TextInput) -> FinalPipelineOutput:
    """Extract amounts from text using 4-step AI pipeline."""
    try:
        # Process with 4-step pipeline
        result = four_step_extractor.extract_from_text(input_data.text)
        
        return result
    
    except Exception as e:
        # Return error in pipeline format
        from app.models.schemas import OCROutput, NormalizationOutput, ClassificationOutput
        
        return FinalPipelineOutput(
            currency=None,
            amounts=[],
            status="error",
            reason=f"Request processing failed: {str(e)}",
            ocr_step=OCROutput(raw_tokens=[], confidence=0.0, status="no_amounts_found"),
            normalization_step=NormalizationOutput(normalized_amounts=[], normalization_confidence=0.0),
            classification_step=ClassificationOutput(amounts=[], confidence=0.0)
        )