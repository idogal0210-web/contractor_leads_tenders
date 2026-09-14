"""
processors — מודולי עיבוד וניתוח נתונים במערכת.
"""
from processors.deduplication import compute_content_hash, is_duplicate, get_existing_item
from processors.ocr import extract_text_from_pdf, extract_text_from_string, OCRResult, OCRMethod
from processors.llm_extractor import extract_opportunity, ExtractedOpportunity, ExtractedField
from processors.classifier import classify_opportunity, OpportunityCategory
from processors.scorer import score_opportunity, OpportunityScore
from processors.matcher import match_to_profile, MatchResult, MatchStatus

__all__ = [
    "compute_content_hash",
    "is_duplicate",
    "get_existing_item",
    "extract_text_from_pdf",
    "extract_text_from_string",
    "OCRResult",
    "OCRMethod",
    "extract_opportunity",
    "ExtractedOpportunity",
    "ExtractedField",
    "classify_opportunity",
    "OpportunityCategory",
    "score_opportunity",
    "OpportunityScore",
    "match_to_profile",
    "MatchResult",
    "MatchStatus",
]
