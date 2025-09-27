"""Helper functions for regex patterns, OCR corrections, currency detection, and text processing."""

import re
from typing import List, Dict, Tuple, Optional
from decimal import Decimal, InvalidOperation


# OCR Error Correction Mappings
OCR_DIGIT_CORRECTIONS = {
    'l': '1',  # lowercase L often mistaken for 1
    'I': '1',  # uppercase i often mistaken for 1
    'O': '0',  # uppercase O often mistaken for 0
    'o': '0',  # lowercase o often mistaken for 0
    'S': '5',  # S sometimes mistaken for 5
    'B': '8',  # B sometimes mistaken for 8
    'G': '6',  # G sometimes mistaken for 6
    'Z': '2',  # Z sometimes mistaken for 2
    'T': '7',  # T sometimes mistaken for 7 in some fonts
}

# Currency patterns and symbols
CURRENCY_PATTERNS = {
    'INR': [r'INR\s*', r'Rs\.?\s*', r'₹\s*', r'Rupees?\s*'],
    'USD': [r'USD\s*', r'\$\s*', r'Dollars?\s*'],
    'EUR': [r'EUR\s*', r'€\s*', r'Euros?\s*'],
    'GBP': [r'GBP\s*', r'£\s*', r'Pounds?\s*'],
}

# Context classification patterns
AMOUNT_TYPE_PATTERNS = {
    'total_bill': [
        r'total[:\s]*',
        r'grand\s+total[:\s]*',
        r'bill\s+amount[:\s]*',
        r'final\s+amount[:\s]*',
        r'net\s+total[:\s]*'
    ],
    'paid': [
        r'paid[:\s]*',
        r'payment[:\s]*',
        r'amount\s+paid[:\s]*',
        r'cash\s+received[:\s]*'
    ],
    'due': [
        r'due[:\s]*',
        r'balance[:\s]*',
        r'outstanding[:\s]*',
        r'pending[:\s]*',
        r'amount\s+due[:\s]*'
    ],
    'discount': [
        r'discount[:\s]*',
        r'off[:\s]*',
        r'reduction[:\s]*',
        r'concession[:\s]*'
    ],
    'tax': [
        r'tax[:\s]*',
        r'gst[:\s]*',
        r'vat[:\s]*',
        r'service\s+tax[:\s]*'
    ],
    'consultation': [
        r'consultation[:\s]*',
        r'doctor\s+fee[:\s]*',
        r'visit\s+charge[:\s]*'
    ],
    'medicine': [
        r'medicine[:\s]*',
        r'drugs?[:\s]*',
        r'medication[:\s]*',
        r'pharmacy[:\s]*'
    ],
    'test': [
        r'test[:\s]*',
        r'lab[:\s]*',
        r'investigation[:\s]*',
        r'pathology[:\s]*'
    ]
}


def correct_ocr_digits(text: str) -> Tuple[str, List[str]]:
    """
    Correct common OCR digit errors in text.
    
    Args:
        text: Input text potentially containing OCR errors
        
    Returns:
        Tuple of (corrected_text, list_of_corrections_made)
    """
    corrections = []
    corrected_text = text
    
    for wrong_char, correct_char in OCR_DIGIT_CORRECTIONS.items():
        if wrong_char in corrected_text:
            # Only correct if it's likely a digit context (surrounded by numbers/spaces)
            pattern = rf'(?<=[\d\s]){re.escape(wrong_char)}(?=[\d\s])|^{re.escape(wrong_char)}(?=\d)|\d{re.escape(wrong_char)}$'
            matches = re.findall(pattern, corrected_text)
            if matches:
                corrected_text = re.sub(pattern, correct_char, corrected_text)
                corrections.append(f"'{wrong_char}' -> '{correct_char}'")
    
    return corrected_text, corrections


def detect_currency(text: str) -> Optional[str]:
    """
    Detect currency from text using patterns.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Detected currency code or None
    """
    text_lower = text.lower()
    
    for currency, patterns in CURRENCY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern.lower(), text_lower):
                return currency
    
    return None


def extract_numeric_tokens(text: str) -> List[str]:
    """
    Extract potential numeric tokens from text.
    
    Args:
        text: Input text
        
    Returns:
        List of potential numeric tokens
    """
    # Pattern to match numbers with optional decimals, commas, and percentage signs
    # Also captures currency symbols adjacent to numbers
    patterns = [
        r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?%?',  # Standard numbers with commas: 1,200.50 or 10%
        r'\d+\.?\d*%?',  # Simple numbers: 1200, 1200.50, 10%
        r'[₹$€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?',  # Currency symbols with numbers
    ]
    
    tokens = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        tokens.extend(matches)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return unique_tokens


def normalize_amount_token(token: str) -> Tuple[Optional[float], float]:
    """
    Convert a token to a numeric amount with confidence.
    
    Args:
        token: String token potentially containing an amount
        
    Returns:
        Tuple of (normalized_amount, confidence_score)
    """
    if not token:
        return None, 0.0
        
    # Remove currency symbols and clean the token
    cleaned_token = re.sub(r'[₹$€£Rs\.INR\s]', '', token)
    
    # Handle percentage - convert to decimal
    is_percentage = cleaned_token.endswith('%')
    if is_percentage:
        cleaned_token = cleaned_token[:-1]
    
    # Remove commas
    cleaned_token = cleaned_token.replace(',', '')
    
    # Correct common OCR errors
    corrected_token, corrections = correct_ocr_digits(cleaned_token)
    
    # Calculate confidence based on corrections needed
    confidence = 1.0
    if corrections:
        confidence -= len(corrections) * 0.1  # Reduce confidence for each correction
        confidence = max(confidence, 0.1)  # Minimum confidence
    
    try:
        amount = float(corrected_token)
        if is_percentage:
            # Convert percentage to decimal (10% -> 0.10)
            amount = amount / 100.0
        return amount, confidence
    except (ValueError, InvalidOperation):
        return None, 0.0


def classify_amount_by_context(amount: float, surrounding_text: str, window_size: int = 50) -> Tuple[str, float]:
    """
    Classify an amount based on surrounding text context.
    
    Args:
        amount: The numeric amount to classify
        surrounding_text: Text around the amount
        window_size: Size of text window to analyze
        
    Returns:
        Tuple of (classification_type, confidence_score)
    """
    text_lower = surrounding_text.lower()
    
    # Find the best matching pattern
    best_match = None
    best_confidence = 0.0
    
    for amount_type, patterns in AMOUNT_TYPE_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Calculate distance from amount mention to pattern
                # This is a simplified approach - in practice, you'd need to locate the amount in text
                confidence = 0.8  # Base confidence for pattern match
                
                # Boost confidence for certain high-confidence patterns
                if pattern in [r'total[:\s]*', r'paid[:\s]*', r'due[:\s]*']:
                    confidence = 0.9
                
                if confidence > best_confidence:
                    best_match = amount_type
                    best_confidence = confidence
    
    return best_match or 'unknown', best_confidence


def extract_source_context(text: str, amount: float, context_window: int = 30) -> str:
    """
    Extract the source text context around an amount.
    
    Args:
        text: Full text content
        amount: Amount to find context for
        context_window: Characters to include on each side
        
    Returns:
        Context string showing where the amount was found
    """
    # Convert amount to string patterns to search for
    amount_patterns = [
        str(int(amount)) if amount.is_integer() else str(amount),
        f"{amount:,.0f}" if amount.is_integer() else f"{amount:,.2f}",
    ]
    
    for pattern in amount_patterns:
        match = re.search(re.escape(pattern), text)
        if match:
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            context = text[start:end].strip()
            return f"text: '{context}'"
    
    return f"amount: {amount}"


def calculate_pipeline_confidence(ocr_conf: float, norm_conf: float, class_conf: float) -> float:
    """
    Calculate overall pipeline confidence from individual step confidences.
    
    Args:
        ocr_conf: OCR step confidence
        norm_conf: Normalization step confidence  
        class_conf: Classification step confidence
        
    Returns:
        Overall pipeline confidence
    """
    # Use weighted geometric mean to ensure all steps contribute
    weights = [0.4, 0.3, 0.3]  # OCR is most important
    confidences = [ocr_conf, norm_conf, class_conf]
    
    # Calculate weighted geometric mean
    weighted_product = 1.0
    for conf, weight in zip(confidences, weights):
        weighted_product *= (conf ** weight)
    
    return min(weighted_product, 1.0)


def is_reasonable_amount(amount: float, min_amount: float = 0.01, max_amount: float = 1000000.0) -> bool:
    """
    Check if an amount is within reasonable bounds for medical bills.
    
    Args:
        amount: Amount to validate
        min_amount: Minimum reasonable amount
        max_amount: Maximum reasonable amount
        
    Returns:
        True if amount is reasonable
    """
    return min_amount <= amount <= max_amount
