"""4-step amount extraction pipeline using AI."""

import json
import re
import base64
import io
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import google.generativeai as genai
from app.config import settings
from app.models.schemas import (
    OCROutput, NormalizationOutput, ClassificationOutput, 
    FinalPipelineOutput, FinalAmount, ClassifiedAmount
)


class FourStepAmountExtractor:
    """4-step pipeline: OCR → Normalization → Classification → Final Output."""
    
    def __init__(self):
        """Initialize the AI service."""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # OCR error correction patterns
        self.ocr_corrections = {
            'l': '1', 'I': '1', '|': '1', 'i': '1',
            'O': '0', 'o': '0', 'Q': '0',
            'S': '5', 's': '5', 'G': '6', 'g': '6',
            'T': '7', 't': '7', 'B': '8', 'b': '8'
        }
    
    def extract_from_image(self, image_data: bytes) -> FinalPipelineOutput:
        """Complete 4-step pipeline from image input."""
        try:
            # Process image to extract text
            image = Image.open(io.BytesIO(image_data))
            
            # Use AI to extract text from image first
            ocr_prompt = """
            Extract ALL text from this medical document image. Focus on:
            - Any numbers that could be amounts
            - Currency symbols (₹, Rs, $, etc.)
            - Context words (total, paid, due, discount, etc.)
            
            Return the raw extracted text exactly as you see it, including any OCR errors.
            """
            
            response = self.model.generate_content([image, ocr_prompt])
            extracted_text = response.text
            
            # Run 4-step pipeline on extracted text
            return self._run_complete_pipeline(extracted_text)
            
        except Exception as e:
            # Return error in pipeline format
            return FinalPipelineOutput(
                currency=None,
                amounts=[],
                status="error",
                reason=f"Image processing error: {str(e)}",
                ocr_step=OCROutput(raw_tokens=[], confidence=0.0, status="no_amounts_found"),
                normalization_step=NormalizationOutput(normalized_amounts=[], normalization_confidence=0.0),
                classification_step=ClassificationOutput(amounts=[], confidence=0.0)
            )
    
    def extract_from_text(self, text: str) -> FinalPipelineOutput:
        """Complete 4-step pipeline from text input."""
        return self._run_complete_pipeline(text)
    
    def _run_complete_pipeline(self, input_text: str) -> FinalPipelineOutput:
        """Run all 4 steps of the pipeline."""
        try:
            # Step 1: OCR/Token Extraction
            ocr_result = self._step1_ocr_extraction(input_text)
            
            if ocr_result.status == "no_amounts_found":
                return FinalPipelineOutput(
                    currency=None,
                    amounts=[],
                    status="no_amounts_found",
                    reason=ocr_result.reason,
                    ocr_step=ocr_result,
                    normalization_step=NormalizationOutput(normalized_amounts=[], normalization_confidence=0.0),
                    classification_step=ClassificationOutput(amounts=[], confidence=0.0)
                )
            
            # Step 2: Normalization
            norm_result = self._step2_normalization(ocr_result.raw_tokens)
            
            # Step 3: Classification
            class_result = self._step3_classification(input_text, norm_result.normalized_amounts)
            
            # Step 4: Final Output
            final_result = self._step4_final_output(
                input_text, ocr_result.currency_hint, class_result.amounts
            )
            
            return FinalPipelineOutput(
                currency=final_result["currency"],
                amounts=final_result["amounts"],
                status="ok",
                ocr_step=ocr_result,
                normalization_step=norm_result,
                classification_step=class_result
            )
            
        except Exception as e:
            return FinalPipelineOutput(
                currency=None,
                amounts=[],
                status="error",
                reason=f"Pipeline error: {str(e)}",
                ocr_step=OCROutput(raw_tokens=[], confidence=0.0, status="no_amounts_found"),
                normalization_step=NormalizationOutput(normalized_amounts=[], normalization_confidence=0.0),
                classification_step=ClassificationOutput(amounts=[], confidence=0.0)
            )
    
    def _step1_ocr_extraction(self, text: str) -> OCROutput:
        """Step 1: Extract raw numeric tokens and currency hints."""
        try:
            prompt = f"""
            Analyze this medical document text and extract ONLY the numeric tokens that could represent amounts.
            
            TEXT: {text}
            
            TASK: Extract raw numeric tokens exactly as they appear (including any OCR errors).
            
            Look for:
            - Numbers that could be amounts (even if they have OCR errors like "l200" or "1O00")
            - Currency symbols or abbreviations (₹, Rs, INR, $, USD, etc.)
            - Percentage signs that might indicate discounts
            
            RETURN ONLY valid JSON in this exact format:
            {{
                "raw_tokens": ["1200", "1000", "200", "10%"],
                "currency_hint": "INR",
                "confidence": 0.74,
                "status": "ok"
            }}
            
            If no amounts found, return:
            {{
                "raw_tokens": [],
                "currency_hint": null,
                "confidence": 0.0,
                "status": "no_amounts_found",
                "reason": "document too noisy"
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = json.loads(self._clean_json_response(response.text))
            
            return OCROutput(
                raw_tokens=result.get("raw_tokens", []),
                currency_hint=result.get("currency_hint"),
                confidence=result.get("confidence", 0.0),
                status=result.get("status", "ok"),
                reason=result.get("reason")
            )
            
        except Exception as e:
            return OCROutput(
                raw_tokens=[],
                confidence=0.0,
                status="no_amounts_found",
                reason=f"OCR extraction failed: {str(e)}"
            )
    
    def _step2_normalization(self, raw_tokens: List[str]) -> NormalizationOutput:
        """Step 2: Fix OCR errors and normalize to clean numbers."""
        try:
            if not raw_tokens:
                return NormalizationOutput(
                    normalized_amounts=[],
                    normalization_confidence=0.0,
                    corrections_made=[]
                )
            
            normalized_amounts = []
            corrections_made = []
            
            for token in raw_tokens:
                # Skip percentage values
                if '%' in token:
                    continue
                
                # Apply OCR corrections
                corrected_token = token
                token_corrections = []
                
                for error_char, correct_char in self.ocr_corrections.items():
                    if error_char in corrected_token:
                        old_token = corrected_token
                        corrected_token = corrected_token.replace(error_char, correct_char)
                        if old_token != corrected_token:
                            token_corrections.append({
                                "original": old_token,
                                "corrected": corrected_token,
                                "rule": f"{error_char} → {correct_char}"
                            })
                
                # Extract numeric value
                numeric_match = re.search(r'[\d.,]+', corrected_token.replace(',', ''))
                if numeric_match:
                    try:
                        value = float(numeric_match.group().replace(',', ''))
                        if settings.MIN_AMOUNT <= value <= settings.MAX_AMOUNT:
                            normalized_amounts.append(value)
                            if token_corrections:
                                corrections_made.extend(token_corrections)
                    except ValueError:
                        continue
            
            confidence = min(1.0, len(normalized_amounts) / max(1, len(raw_tokens)))
            
            return NormalizationOutput(
                normalized_amounts=normalized_amounts,
                normalization_confidence=confidence,
                corrections_made=corrections_made
            )
            
        except Exception as e:
            return NormalizationOutput(
                normalized_amounts=[],
                normalization_confidence=0.0,
                corrections_made=[]
            )
    
    def _step3_classification(self, original_text: str, amounts: List[float]) -> ClassificationOutput:
        """Step 3: Classify amounts by context (total, paid, due, etc.)."""
        try:
            if not amounts:
                return ClassificationOutput(amounts=[], confidence=0.0)
            
            prompt = f"""
            Classify these amounts by their context in the medical document.
            
            ORIGINAL TEXT: {original_text}
            AMOUNTS TO CLASSIFY: {amounts}
            
            For each amount, determine its type based on surrounding text:
            - total_bill: Final total, grand total, amount due
            - paid: Amount paid, payment received, advance
            - due: Balance due, pending amount, outstanding
            - consultation: Doctor fee, consultation charge
            - medicine: Medicine cost, pharmacy bill, medication
            - test: Lab test, investigation, scan cost
            - tax: GST, VAT, service tax, CGST, SGST
            - discount: Discount, offer, concession
            
            RETURN ONLY valid JSON:
            {{
                "amounts": [
                    {{"type": "total_bill", "value": 1200}},
                    {{"type": "paid", "value": 1000}},
                    {{"type": "due", "value": 200}}
                ],
                "confidence": 0.80
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = json.loads(self._clean_json_response(response.text))
            
            classified_amounts = []
            for item in result.get("amounts", []):
                classified_amounts.append(ClassifiedAmount(
                    type=item.get("type", "unknown"),
                    value=float(item.get("value", 0))
                ))
            
            return ClassificationOutput(
                amounts=classified_amounts,
                confidence=result.get("confidence", 0.0)
            )
            
        except Exception as e:
            # Fallback: classify as unknown
            classified_amounts = []
            for amount in amounts:
                classified_amounts.append(ClassifiedAmount(type="unknown", value=amount))
            
            return ClassificationOutput(amounts=classified_amounts, confidence=0.5)
    
    def _step4_final_output(self, original_text: str, currency: Optional[str], classified_amounts: List[ClassifiedAmount]) -> Dict[str, Any]:
        """Step 4: Generate final output with provenance."""
        try:
            final_amounts = []
            
            for amount_obj in classified_amounts:
                # Find source text for this amount
                amount_str = str(int(amount_obj.value)) if amount_obj.value.is_integer() else str(amount_obj.value)
                
                # Look for context around this amount in the original text
                source_context = self._find_source_context(original_text, amount_str, amount_obj.type)
                
                final_amounts.append(FinalAmount(
                    type=amount_obj.type,
                    value=amount_obj.value,
                    source=source_context
                ))
            
            return {
                "currency": currency or settings.DEFAULT_CURRENCY,
                "amounts": final_amounts
            }
            
        except Exception as e:
            return {
                "currency": settings.DEFAULT_CURRENCY,
                "amounts": []
            }
    
    def _find_source_context(self, text: str, amount_str: str, amount_type: str) -> str:
        """Find the source text snippet for an amount."""
        # Look for the amount in the text with some context
        lines = text.split('\n')
        
        for line in lines:
            if amount_str in line:
                return f"text: '{line.strip()}'"
        
        # If not found, create a generic source based on type
        type_mapping = {
            "total_bill": "Total",
            "paid": "Paid",
            "due": "Due", 
            "consultation": "Consultation",
            "medicine": "Medicine",
            "test": "Test",
            "tax": "Tax",
            "discount": "Discount"
        }
        
        context_word = type_mapping.get(amount_type, "Amount")
        return f"text: '{context_word}: {amount_str}'"
    
    def _clean_json_response(self, text: str) -> str:
        """Clean AI response to extract valid JSON."""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        
        # Find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text.strip()


# Global service instance
four_step_extractor = FourStepAmountExtractor()