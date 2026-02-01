"""
Text Cleaner Module
Handles text preprocessing and cleaning for LLM input
"""

import re
import unicodedata
from typing import Optional


class TextCleaner:
    """
    Text cleaning utility for preparing text for LLM processing
    """
    
    def __init__(self):
        # Common contractions mapping
        self.contractions = {
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'re": " are",
            "'s": " is",
            "'d": " would",
            "'ll": " will",
            "'ve": " have",
            "'m": " am"
        }
    
    def clean(self, text: str) -> str:
        """
        Main cleaning pipeline
        
        Args:
            text: Raw input text
            
        Returns:
            Cleaned text ready for LLM processing
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Apply cleaning steps in order
        text = self.normalize_unicode(text)
        text = self.remove_urls(text)
        text = self.remove_emails(text)
        text = self.remove_html_tags(text)
        text = self.normalize_whitespace(text)
        text = self.remove_special_characters(text)
        text = self.normalize_quotes(text)
        text = self.fix_common_issues(text)
        text = self.final_cleanup(text)
        
        return text.strip()
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to standard form"""
        # Normalize to NFKC form (compatibility decomposition, followed by canonical composition)
        text = unicodedata.normalize('NFKC', text)
        return text
    
    def remove_urls(self, text: str) -> str:
        """Remove URLs from text"""
        # Match http, https, ftp URLs
        url_pattern = r'https?://\S+|www\.\S+|ftp://\S+'
        text = re.sub(url_pattern, '', text)
        return text
    
    def remove_emails(self, text: str) -> str:
        """Remove email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        text = re.sub(email_pattern, '', text)
        return text
    
    def remove_html_tags(self, text: str) -> str:
        """Remove HTML tags from text"""
        # Remove HTML tags
        html_pattern = r'<[^>]+>'
        text = re.sub(html_pattern, '', text)
        
        # Decode common HTML entities
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
            '&ndash;': '-',
            '&mdash;': '-',
            '&hellip;': '...',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™'
        }
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize all whitespace characters"""
        # Replace various whitespace characters with standard space
        text = re.sub(r'[\t\r\f\v]+', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        return text
    
    def remove_special_characters(self, text: str) -> str:
        """Remove or replace special characters"""
        # Keep basic punctuation and alphanumeric, remove weird symbols
        # But preserve sentence structure
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Replace fancy quotes and dashes with standard ones
        replacements = {
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '–': '-',
            '—': '-',
            '…': '...',
            '•': '-',
            '·': '-',
            '→': '->',
            '←': '<-',
            '≈': '~',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def normalize_quotes(self, text: str) -> str:
        """Normalize quotation marks"""
        # Ensure consistent quote usage
        text = re.sub(r'[""„‟]', '"', text)
        text = re.sub(r"[''‚‛]", "'", text)
        return text
    
    def fix_common_issues(self, text: str) -> str:
        """Fix common text issues"""
        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])(?=[A-Za-z])', r'\1 ', text)
        
        # Fix multiple punctuation
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r'\?{2,}', '?', text)
        text = re.sub(r'!{2,}', '!', text)
        
        # Fix spacing around parentheses
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        
        # Fix spacing around brackets
        text = re.sub(r'\[\s+', '[', text)
        text = re.sub(r'\s+\]', ']', text)
        
        return text
    
    def expand_contractions(self, text: str) -> str:
        """Expand contractions (optional, not used by default)"""
        for contraction, expansion in self.contractions.items():
            text = re.sub(re.escape(contraction), expansion, text, flags=re.IGNORECASE)
        return text
    
    def final_cleanup(self, text: str) -> str:
        """Final cleanup pass"""
        # Remove leading/trailing whitespace from each line
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        
        # Remove empty lines at start and end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        
        # Rejoin
        text = '\n'.join(lines)
        
        # Final whitespace normalization
        text = re.sub(r' {2,}', ' ', text)
        
        return text
    
    def get_statistics(self, original: str, cleaned: str) -> dict:
        """Get cleaning statistics"""
        return {
            'original_length': len(original),
            'cleaned_length': len(cleaned),
            'characters_removed': len(original) - len(cleaned),
            'reduction_percentage': round((1 - len(cleaned) / len(original)) * 100, 2) if original else 0,
            'original_word_count': len(original.split()),
            'cleaned_word_count': len(cleaned.split()),
            'original_line_count': len(original.split('\n')),
            'cleaned_line_count': len(cleaned.split('\n'))
        }


# Testing
if __name__ == '__main__':
    cleaner = TextCleaner()
    
    # Test text with various issues
    test_text = """
    This is a   test    text with    multiple   spaces.
    
    
    
    It has URLs like https://example.com and emails like test@email.com
    
    <p>HTML tags</p> and &nbsp; entities &amp; more...
    
    "Smart quotes" and 'apostrophes' with em—dashes and ellipsis…
    
    Some     weird      spacing   issues  .And missing spaces,after punctuation
    
    """
    
    cleaned = cleaner.clean(test_text)
    stats = cleaner.get_statistics(test_text, cleaned)
    
    print("Original text:")
    print("-" * 40)
    print(repr(test_text))
    print("\nCleaned text:")
    print("-" * 40)
    print(repr(cleaned))
    print("\nStatistics:")
    print("-" * 40)
    for key, value in stats.items():
        print(f"  {key}: {value}")
