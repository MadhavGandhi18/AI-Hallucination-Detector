"""
Claim Extractor Module
Uses Ollama LLM to extract verifiable claims from text
"""

import json
import time
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClaimExtractor:
    """
    Extract claims from text using Ollama LLM
    """
    
    def __init__(self, 
                 model: str = "llama3.2:3b",
                 ollama_url: str = "http://localhost:11434"):
        """
        Initialize the claim extractor
        
        Args:
            model: Ollama model to use (default: llama3.2)
            ollama_url: Ollama API base URL
        """
        self.model = model
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
        
    def check_ollama_connection(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_available_models(self) -> list:
        """Get list of available models in Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.exceptions.RequestException:
            return []
    
    def create_extraction_prompt(self, text: str) -> str:
        """
        Create the prompt for claim extraction
        
        Args:
            text: The text to extract claims from
            
        Returns:
            Formatted prompt for the LLM
        """
        prompt = f"""Extract all individual factual claims from the following text. 

IMPORTANT RULES:
1. Break down compound claims into separate atomic claims
2. Each claim should contain ONE verifiable fact only
3. If a sentence has multiple facts, split them into separate claims

Example:
Input: "Tesla was founded by Elon Musk in 2003 in California"
Output claims:
- "Tesla was founded by Elon Musk"
- "Tesla was founded in 2003"
- "Tesla was founded in California"

TEXT TO ANALYZE:
\"\"\"
{text}
\"\"\"

Return ONLY a valid JSON object with this exact format:
{{"claims": ["claim 1", "claim 2", "claim 3"]}}

Extract all atomic claims now:"""
        
        return prompt
    
    def parse_llm_response(self, response_text: str) -> dict:
        """
        Parse the LLM response to extract JSON
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed claims dictionary
        """
        try:
            # Try to parse as JSON directly
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        try:
            # Look for JSON object pattern
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array pattern
        try:
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                claims_list = json.loads(json_str)
                return {"claims": claims_list}
        except json.JSONDecodeError:
            pass
        
        logger.warning(f"Could not parse LLM response as JSON: {response_text[:200]}...")
        return {"claims": [], "parse_error": True, "raw_response": response_text}
    
    def extract_claims(self, text: str) -> dict:
        """
        Extract claims from text using Ollama LLM
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary containing extracted claims and metadata
        """
        start_time = time.time()
        
        # Check if Ollama is running
        if not self.check_ollama_connection():
            return {
                'success': False,
                'error': 'Ollama is not running. Please start Ollama with: ollama serve',
                'claims': [],
                'total_claims': 0,
                'processing_time': 0
            }
        
        # Check if model is available
        available_models = self.get_available_models()
        if not any(self.model in m for m in available_models):
            return {
                'success': False,
                'error': f'Model "{self.model}" not found. Available models: {available_models}. Pull it with: ollama pull {self.model}',
                'claims': [],
                'total_claims': 0,
                'processing_time': 0
            }
        
        # Create prompt
        prompt = self.create_extraction_prompt(text)
        
        try:
            # Call Ollama API
            response = requests.post(
                self.api_endpoint,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.1,  # Low temperature for consistent output
                        'num_predict': 2048,  # Max tokens to generate
                    }
                },
                timeout=120  # 2 minute timeout for longer texts
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Ollama API error: {response.status_code}',
                    'claims': [],
                    'total_claims': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Parse response
            result = response.json()
            llm_response = result.get('response', '')
            
            # Extract claims from response
            parsed = self.parse_llm_response(llm_response)
            claims = parsed.get('claims', [])
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'claims': claims,
                'total_claims': len(claims),
                'processing_time': round(processing_time, 2),
                'model_used': self.model
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timed out. The text might be too long.',
                'claims': [],
                'total_claims': 0,
                'processing_time': time.time() - start_time
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'claims': [],
                'total_claims': 0,
                'processing_time': time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Unexpected error in claim extraction: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'claims': [],
                'total_claims': 0,
                'processing_time': time.time() - start_time
            }


# Testing
if __name__ == '__main__':
    extractor = ClaimExtractor()
    
    # Check connection
    print("Checking Ollama connection...")
    if extractor.check_ollama_connection():
        print("✓ Ollama is running")
        print(f"Available models: {extractor.get_available_models()}")
    else:
        print("✗ Ollama is not running. Start it with: ollama serve")
        exit(1)
    
    # Test extraction
    test_text = """
    The Eiffel Tower was built in 1889 and stands 330 meters tall. 
    It was designed by Gustave Eiffel's engineering company. 
    Every year, approximately 7 million people visit the tower.
    Paris is the capital of France and has a population of over 2 million people.
    The tower was originally intended to stand for only 20 years.
    """
    
    print("\nExtracting claims from test text...")
    print("-" * 50)
    
    result = extractor.extract_claims(test_text)
    
    print(json.dumps(result, indent=2))
