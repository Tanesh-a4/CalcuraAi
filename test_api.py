"""Simple test script to verify the AI-powered amount detection works."""

import requests
import json
import base64

# Server URL
BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:", response.json())

def test_text_extraction():
    """Test text-based amount extraction with 4-step pipeline."""
    # Test case matching the problem statement format
    test_text = """
    Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%
    
    Medical Bill - ABC Hospital
    Patient: John Doe
    Date: 2024-01-15
    
    Consultation Fee: ₹500
    Medicine: ₹250
    Lab Tests: ₹300
    GST (18%): ₹189
    
    Total Amount: ₹1239
    """
    
    data = {"text": test_text}
    response = requests.post(f"{BASE_URL}/api/v1/extract-from-text", json=data)
    
    print("4-Step Pipeline Result:")
    print("=" * 60)
    result = response.json()
    
    # Display each step
    print("STEP 1 - OCR/Token Extraction:")
    ocr_step = result.get("ocr_step", {})
    print(f"  Raw Tokens: {ocr_step.get('raw_tokens', [])}")
    print(f"  Currency Hint: {ocr_step.get('currency_hint')}")
    print(f"  Confidence: {ocr_step.get('confidence', 0)}")
    print(f"  Status: {ocr_step.get('status')}")
    
    print("\nSTEP 2 - Normalization:")
    norm_step = result.get("normalization_step", {})
    print(f"  Normalized Amounts: {norm_step.get('normalized_amounts', [])}")
    print(f"  Confidence: {norm_step.get('normalization_confidence', 0)}")
    print(f"  Corrections Made: {len(norm_step.get('corrections_made', []))}")
    
    print("\nSTEP 3 - Classification:")
    class_step = result.get("classification_step", {})
    amounts = class_step.get("amounts", [])
    for amount in amounts:
        print(f"  Type: {amount.get('type')}, Value: {amount.get('value')}")
    print(f"  Confidence: {class_step.get('confidence', 0)}")
    
    print("\nSTEP 4 - Final Output:")
    print(f"  Currency: {result.get('currency')}")
    print(f"  Status: {result.get('status')}")
    final_amounts = result.get("amounts", [])
    for amount in final_amounts:
        print(f"    {amount.get('type')}: {amount.get('value')} - {amount.get('source')}")
    
    print("\nFull JSON Response:")
    print(json.dumps(result, indent=2))

def test_ocr_simulation():
    """Test with OCR-style errors as mentioned in problem statement."""
    # Simulate OCR output with errors: T0tal: Rs l200 | Pald: 1000 | Due: 200
    ocr_text = """
    T0tal: Rs l200 | Pald: l000 | Due: 2OO
    
    Medical Blll - XYZ Clinic
    Patient: Jane D0e
    
    C0nsultati0n: Rs 5OO
    Medlcine: Rs 25O
    Lab Test: Rs 3OO
    """
    
    data = {"text": ocr_text}
    response = requests.post(f"{BASE_URL}/api/v1/extract-from-text", json=data)
    
    print("OCR Error Correction Test:")
    print("=" * 60)
    print(f"Input (with OCR errors): {ocr_text}")
    
    result = response.json()
    
    # Check normalization step for corrections
    norm_step = result.get("normalization_step", {})
    corrections = norm_step.get("corrections_made", [])
    
    print(f"\nCorrections Applied: {len(corrections)}")
    for correction in corrections:
        print(f"  {correction.get('original')} → {correction.get('corrected')} ({correction.get('rule')})")
    
    print(f"\nFinal Results:")
    final_amounts = result.get("amounts", [])
    for amount in final_amounts:
        print(f"  {amount.get('type')}: {amount.get('value')}")

def test_image_extraction():
    """Test image-based amount extraction."""
    try:
        with open("medical_bill.jpg", "rb") as f:
            files = {"file": f}
            response = requests.post(f"{BASE_URL}/api/v1/extract-from-image", files=files)
            
            print("Image Extraction Test:")
            print("=" * 60)
            result = response.json()
            
            print(f"Status: {result.get('status')}")
            print(f"Currency: {result.get('currency')}")
            
            amounts = result.get("amounts", [])
            print(f"Found {len(amounts)} amounts:")
            for amount in amounts:
                print(f"  {amount.get('type')}: {amount.get('value')} - {amount.get('source')}")
                
    except FileNotFoundError:
        print("Image test skipped - no medical_bill.jpg file found")

if __name__ == "__main__":
    try:
        print("Testing AI-Powered Amount Detector...")
        print("=" * 50)
        
        test_health()
        print()
        
        test_text_extraction()
        print()
        
        test_ocr_simulation()
        print()
        
        test_image_extraction()
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure it's running on port 8001")
    except Exception as e:
        print(f"Error: {e}")