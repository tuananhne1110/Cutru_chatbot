"""
Utility functions for text processing and encoding fixes
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def fix_utf8_encoding(text: str) -> str:
    """
    Automatically detect and fix various UTF-8 encoding issues.
    
    This function tries multiple encoding repair strategies and selects 
    the best result based on text quality metrics.
    
    Args:
        text: Input text that may have encoding issues
        
    Returns:
        Fixed text with proper UTF-8 encoding
    """
    if not text or not isinstance(text, str):
        return text
    
    original_text = text
    candidates = [text]  # Start with original text
    
    try:
        # Strategy 1: URL decode
        if '%' in text:
            import urllib.parse
            try:
                decoded = urllib.parse.unquote(text, encoding='utf-8', errors='ignore')
                if decoded != text:
                    candidates.append(decoded)
            except Exception:
                pass
        
        # Strategy 2: Try common encoding pairs
        encoding_pairs = [
            ('latin-1', 'utf-8'),
            ('cp1252', 'utf-8'),
            ('iso-8859-1', 'utf-8'),
            ('utf-8', 'latin-1'),  # Sometimes double-encoded
        ]
        
        for source_enc, target_enc in encoding_pairs:
            try:
                # Try decode with source encoding, then encode to target
                if source_enc == 'utf-8':
                    # For utf-8 source, encode first then decode
                    fixed = text.encode(target_enc, errors='ignore').decode(source_enc, errors='ignore')
                else:
                    # For other sources, encode as source then decode as target
                    fixed = text.encode(source_enc, errors='ignore').decode(target_enc, errors='ignore')
                
                if fixed and fixed != text:
                    candidates.append(fixed)
            except Exception:
                pass
        
        # Strategy 3: Try ftfy library if available (fixes mojibake automatically)
        try:
            import ftfy
            fixed = ftfy.fix_text(text)
            if fixed != text:
                candidates.append(fixed)
        except ImportError:
            pass  # ftfy not available, skip this strategy
        
        # Strategy 4: Manual mojibake patterns (fallback)
        # Look for common mojibake patterns and try to fix them
        if any(ord(c) > 127 for c in text):  # Contains non-ASCII
            try:
                # Try latin-1 -> utf-8 conversion
                fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
                if fixed != text:
                    candidates.append(fixed)
            except Exception:
                pass
        
        # Evaluate all candidates and pick the best one
        best_candidate = _select_best_text(candidates)
        
        if best_candidate != original_text:
            logger.info(f"Fixed encoding: '{original_text}' -> '{best_candidate}'")
        
        return best_candidate
        
    except Exception as e:
        logger.warning(f"Error fixing encoding for text '{text}': {e}")
        return original_text

def _select_best_text(candidates):
    """
    Select the best text candidate based on multiple quality metrics.
    
    Args:
        candidates: List of text candidates
        
    Returns:
        Best candidate text
    """
    if not candidates:
        return ""
    
    if len(candidates) == 1:
        return candidates[0]
    
    # Score each candidate
    scored_candidates = []
    for candidate in candidates:
        score = _calculate_text_quality_score(candidate)
        scored_candidates.append((score, candidate))
    
    # Sort by score (highest first)
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    return scored_candidates[0][1]

def _calculate_text_quality_score(text: str) -> float:
    """
    Calculate quality score for text based on various metrics.
    Higher score = better quality text.
    
    Args:
        text: Text to evaluate
        
    Returns:
        Quality score (0.0 to 1.0)
    """
    if not text:
        return 0.0
    
    score = 0.0
    
    # 1. Vietnamese language score (0-0.4)
    vietnamese_score = _get_vietnamese_score(text)
    score += vietnamese_score * 0.4
    
    # 2. Character validity score (0-0.3)
    # Penalize mojibake characters
    mojibake_chars = ['Ã', 'Â', 'Ä', 'Ð', 'Ñ', 'Õ', 'Ö', 'Ø', 'Ù', 'Ú', 'Û', 'Ü', 'â€', 'â€™']
    mojibake_count = sum(1 for char in mojibake_chars if char in text)
    validity_score = max(0.0, 1.0 - (mojibake_count / len(text)))
    score += validity_score * 0.3
    
    # 3. Readability score (0-0.2)
    # Prefer text with normal word patterns
    words = text.split()
    if words:
        avg_word_length = sum(len(word) for word in words) / len(words)
        # Ideal word length for Vietnamese is around 4-6 characters
        readability_score = 1.0 - abs(avg_word_length - 5.0) / 10.0
        readability_score = max(0.0, min(1.0, readability_score))
        score += readability_score * 0.2
    
    # 4. Special character penalty (0-0.1)
    # Penalize excessive special characters (except Vietnamese diacritics)
    special_char_count = sum(1 for c in text if not c.isalnum() and c not in ' .,?!-\n\t')
    if len(text) > 0:
        special_ratio = special_char_count / len(text)
        special_score = max(0.0, 1.0 - special_ratio * 2)  # Max 50% special chars
        score += special_score * 0.1
    
    return min(1.0, score)

def _get_vietnamese_score(text: str) -> float:
    """
    Calculate how much the text looks like Vietnamese.
    
    Returns:
        Score from 0.0 to 1.0
    """
    if not text:
        return 0.0
    
    text_lower = text.lower()
    
    # Vietnamese diacritics
    vietnamese_chars = [
        'á', 'à', 'ả', 'ã', 'ạ', 'ă', 'ắ', 'ằ', 'ẳ', 'ẵ', 'ặ',
        'â', 'ấ', 'ầ', 'ẩ', 'ẫ', 'ậ', 'é', 'è', 'ẻ', 'ẽ', 'ẹ',
        'ê', 'ế', 'ề', 'ể', 'ễ', 'ệ', 'í', 'ì', 'ỉ', 'ĩ', 'ị',
        'ó', 'ò', 'ỏ', 'õ', 'ọ', 'ô', 'ố', 'ồ', 'ổ', 'ỗ', 'ộ',
        'ơ', 'ớ', 'ờ', 'ở', 'ỡ', 'ợ', 'ú', 'ù', 'ủ', 'ũ', 'ụ',
        'ư', 'ứ', 'ừ', 'ử', 'ữ', 'ự', 'ý', 'ỳ', 'ỷ', 'ỹ', 'ỵ', 'đ'
    ]
    
    # Common Vietnamese words
    vietnamese_words = [
        'đăng', 'ký', 'tạm', 'trú', 'là', 'gì', 'như', 'thế', 'nào',
        'của', 'với', 'và', 'cho', 'từ', 'được', 'có', 'không', 'này',
        'khi', 'sẽ', 'những', 'để', 'về', 'trong', 'một', 'các', 'người',
        'thời', 'gian', 'nơi', 'cần', 'phải', 'theo', 'tại', 'công', 'việc'
    ]
    
    score = 0.0
    
    # Character-based scoring (0.0 - 0.6)
    vietnamese_char_count = sum(1 for char in text_lower if char in vietnamese_chars)
    if len(text) > 0:
        char_ratio = vietnamese_char_count / len(text)
        score += min(0.6, char_ratio * 3)  # Up to 60% for character presence
    
    # Word-based scoring (0.0 - 0.4)
    words = text_lower.split()
    if words:
        vietnamese_word_count = sum(1 for word in words if word in vietnamese_words)
        word_ratio = vietnamese_word_count / len(words)
        score += min(0.4, word_ratio * 2)  # Up to 40% for word presence
    
    return min(1.0, score)

def _is_vietnamese_text(text: str) -> bool:
    """
    Check if text contains Vietnamese characteristics
    """
    return _get_vietnamese_score(text) > 0.1

def normalize_vietnamese_text(text: str) -> str:
    """
    Normalize Vietnamese text for better processing
    """
    if not text:
        return text
    
    # Fix encoding first
    text = fix_utf8_encoding(text)
    
    # Basic normalization
    text = text.strip()
    
    # Remove extra whitespace
    import re
    text = re.sub(r'\s+', ' ', text)
    
    return text
