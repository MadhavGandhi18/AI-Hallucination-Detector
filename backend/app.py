"""
Hallucination Detector Backend
Flask API for text cleaning and claim extraction using Ollama LLM
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from text_cleaner import TextCleaner
from claim_extractor import ClaimExtractor
import logging
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize components
text_cleaner = TextCleaner()
claim_extractor = ClaimExtractor()

# Lazy load verifier (only when needed)
claim_verifier = None

def get_claim_verifier():
    global claim_verifier
    if claim_verifier is None:
        from claim_verifier import ClaimVerifier
        # Use Ollama (local LLM) - no API key needed
        claim_verifier = ClaimVerifier()
    return claim_verifier

# Output directory for claims JSON
OUTPUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIMS_FILE = os.path.join(OUTPUT_DIR, 'extracted_claims.json')
VERIFIED_FILE = os.path.join(OUTPUT_DIR, 'verified_claims.json')


def save_claims_to_file(claims, cleaned_text, processing_time):
    """Save extracted claims to JSON file"""
    data = {
        'timestamp': datetime.now().isoformat(),
        'cleaned_text': cleaned_text,
        'total_claims': len(claims),
        'processing_time': processing_time,
        'claims': claims
    }
    
    with open(CLAIMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Claims saved to {CLAIMS_FILE}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Hallucination Detector API is running'
    })


@app.route('/api/clean-text', methods=['POST'])
def clean_text():
    """
    Endpoint to clean input text
    
    Request body:
    {
        "text": "Your text here..."
    }
    
    Returns:
    {
        "success": true,
        "original_length": 1000,
        "cleaned_length": 950,
        "cleaned_text": "Cleaned text..."
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        original_text = data['text']
        cleaned_text = text_cleaner.clean(original_text)
        
        return jsonify({
            'success': True,
            'original_length': len(original_text),
            'cleaned_length': len(cleaned_text),
            'cleaned_text': cleaned_text
        })
        
    except Exception as e:
        logger.error(f"Error cleaning text: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/extract-claims', methods=['POST'])
def extract_claims():
    """
    Endpoint to extract claims from text using LLM
    
    Request body:
    {
        "text": "Your text here...",
        "clean_first": true  // Optional, default true
    }
    
    Returns:
    {
        "success": true,
        "claims": [
            {
                "id": 1,
                "claim": "The claim text",
                "category": "factual/statistical/historical/scientific/etc",
                "confidence": 0.95
            }
        ],
        "total_claims": 5,
        "processing_time": 2.5
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        text = data['text']
        clean_first = data.get('clean_first', True)
        
        # Clean text if requested
        if clean_first:
            text = text_cleaner.clean(text)
        
        # Extract claims using LLM
        result = claim_extractor.extract_claims(text)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error extracting claims: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    """
    Full analysis endpoint - cleans text and extracts claims
    
    Request body:
    {
        "text": "Your text here..."
    }
    
    Returns combined cleaning and extraction results
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        original_text = data['text']
        
        # Step 1: Clean the text
        cleaned_text = text_cleaner.clean(original_text)
        
        # Step 2: Extract claims
        extraction_result = claim_extractor.extract_claims(cleaned_text)
        
        # Step 3: Save claims to JSON file
        if extraction_result.get('success'):
            save_claims_to_file(
                extraction_result.get('claims', []),
                cleaned_text,
                extraction_result.get('processing_time', 0)
            )
        
        return jsonify({
            'success': True,
            'original_text_length': len(original_text),
            'cleaned_text_length': len(cleaned_text),
            'cleaned_text': cleaned_text,
            'claims': extraction_result.get('claims', []),
            'total_claims': extraction_result.get('total_claims', 0),
            'processing_time': extraction_result.get('processing_time', 0)
        })
        
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/verify', methods=['POST'])
def verify_claims():
    """
    Verify extracted claims using Gemini API and web search
    
    Request body:
    {
        "claims": ["claim1", "claim2", ...]  // Optional, uses extracted_claims.json if not provided
    }
    
    Returns verification results with confidence scores
    """
    try:
        verifier = get_claim_verifier()
        
        data = request.get_json() or {}
        claims = data.get('claims')
        
        # If no claims provided, load from extracted_claims.json
        if not claims:
            if not os.path.exists(CLAIMS_FILE):
                return jsonify({
                    'success': False,
                    'error': 'No claims provided and no extracted_claims.json found. Run /api/analyze first.'
                }), 400
            
            with open(CLAIMS_FILE, 'r', encoding='utf-8') as f:
                extracted = json.load(f)
                claims = extracted.get('claims', [])
        
        if not claims:
            return jsonify({
                'success': False,
                'error': 'No claims to verify'
            }), 400
        
        # Verify all claims
        verification_result = verifier.verify_all_claims(claims)
        
        # Save to verified_claims.json
        with open(VERIFIED_FILE, 'w', encoding='utf-8') as f:
            json.dump(verification_result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Verification complete. Results saved to {VERIFIED_FILE}")
        
        return jsonify({
            'success': True,
            **verification_result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in verification: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/claims', methods=['GET'])
def get_claims():
    """Get the extracted claims from JSON file"""
    try:
        if not os.path.exists(CLAIMS_FILE):
            return jsonify({
                'success': False,
                'error': 'No extracted claims found. Run /api/analyze first.'
            }), 404
        
        with open(CLAIMS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({
            'success': True,
            **data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/verified', methods=['GET'])
def get_verified():
    """Get the verified claims from JSON file"""
    try:
        if not os.path.exists(VERIFIED_FILE):
            return jsonify({
                'success': False,
                'error': 'No verified claims found. Run /api/verify first.'
            }), 404
        
        with open(VERIFIED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({
            'success': True,
            **data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🔍 Hallucination Detector Backend (Ollama)")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("Endpoints:")
    print("  GET  /health          - Health check")
    print("  POST /api/clean-text  - Clean input text")
    print("  POST /api/extract-claims - Extract claims from text")
    print("  POST /api/analyze     - Full analysis pipeline")
    print("  POST /api/verify      - Verify extracted claims")
    print("  GET  /api/claims      - Get extracted claims")
    print("  GET  /api/verified    - Get verified claims")
    print("=" * 50)
    print("✓ Using Ollama (llama3.2:3b) for all LLM tasks")
    print("  Make sure Ollama is running: ollama serve")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
