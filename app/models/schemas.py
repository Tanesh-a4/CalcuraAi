"""Pydantic schemas for 4-step amount detection pipeline."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# Step 1 - OCR/Text Extraction Models
class OCROutput(BaseModel):
    """Output from Step 1: OCR token extraction."""
    raw_tokens: List[str] = Field(..., description="Extracted numeric tokens from text/image")
    currency_hint: Optional[str] = Field(None, description="Detected currency (INR, USD, etc.)")
    confidence: float = Field(..., description="Overall OCR confidence score (0.0-1.0)")
    status: Literal["ok", "no_amounts_found"] = Field(default="ok")
    reason: Optional[str] = Field(None, description="Reason for failure if status != ok")


# Step 2 - Normalization Models  
class NormalizationOutput(BaseModel):
    """Output from Step 2: Numeric normalization."""
    normalized_amounts: List[float] = Field(..., description="Corrected numeric amounts")
    normalization_confidence: float = Field(..., description="Confidence in corrections (0.0-1.0)")
    corrections_made: List[dict] = Field(default_factory=list, description="List of OCR corrections applied")


# Step 3 - Classification Models
class ClassifiedAmount(BaseModel):
    """Individual classified amount."""
    type: str = Field(..., description="Amount type (total_bill, paid, due, etc.)")
    value: float = Field(..., description="The numeric amount value")


class ClassificationOutput(BaseModel):
    """Output from Step 3: Context classification."""
    amounts: List[ClassifiedAmount] = Field(..., description="Classified amounts")
    confidence: float = Field(..., description="Classification confidence (0.0-1.0)")


# Step 4 - Final Output Models
class FinalAmount(BaseModel):
    """Final amount with provenance."""
    type: str = Field(..., description="Amount type classification")
    value: float = Field(..., description="Numeric amount value")
    source: str = Field(..., description="Source text snippet that contained this amount")


class FinalPipelineOutput(BaseModel):
    """Final Step 4 output with all pipeline results."""
    currency: Optional[str] = Field(None, description="Detected currency")
    amounts: List[FinalAmount] = Field(..., description="All detected and classified amounts")
    status: Literal["ok", "no_amounts_found", "error"] = Field(default="ok")
    reason: Optional[str] = Field(None, description="Reason for failure if status != ok")
    
    # Pipeline step details
    ocr_step: OCROutput = Field(..., description="Step 1 OCR results")
    normalization_step: NormalizationOutput = Field(..., description="Step 2 normalization results")
    classification_step: ClassificationOutput = Field(..., description="Step 3 classification results")


# Legacy models for backward compatibility
class AmountResult(BaseModel):
    """Individual amount extraction result."""
    value: float = Field(..., description="Extracted amount value")
    currency: str = Field(default="INR", description="Currency code")
    type: str = Field(default="unknown", description="Amount type (total_bill, consultation, etc.)")
    context: str = Field(default="", description="Context or description")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    raw_text: Optional[str] = Field(None, description="Original text where amount was found")


class ExtractionSummary(BaseModel):
    """Summary of extraction results."""
    total_found: int = Field(..., description="Total number of amounts found")
    highest_confidence: float = Field(..., description="Highest confidence score")
    primary_amount: float = Field(..., description="Most likely primary amount")
    primary_type: str = Field(..., description="Type of primary amount")


class TextInput(BaseModel):
    """Input for text-based amount extraction."""
    text: str = Field(..., description="Text content to analyze")


class ExtractionResponse(BaseModel):
    """Response from amount extraction."""
    success: bool = Field(..., description="Whether extraction was successful")
    amounts: List[AmountResult] = Field(default_factory=list, description="Extracted amounts")
    summary: Optional[ExtractionSummary] = Field(None, description="Extraction summary")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
