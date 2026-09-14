"""
core/db/enums.py — הגדרות Enum מרכזיות עבור כל ישויות המערכת.

מודול עצמאי ללא תלות בספריות חיצוניות (משתמש ב-enum סטנדרטי של פייתון).
"""
from __future__ import annotations

import enum


class OpportunityType(str, enum.Enum):
    TENDER = "tender"
    LEAD = "lead"


class OpportunityCategory(str, enum.Enum):
    SERVICE_REQUEST = "service_request"
    PROVIDER_AD = "provider_ad"
    RECOMMENDATION_REQUEST = "recommendation_request"
    SUBCONTRACTING = "subcontracting"
    IRRELEVANT = "irrelevant"
    UNCERTAIN = "uncertain"


class MatchStatus(str, enum.Enum):
    FIT = "fit"
    NO_FIT = "no_fit"
    NEEDS_REVIEW = "needs_review"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    NEEDS_HUMAN = "needs_human"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class SourceType(str, enum.Enum):
    GOV_API = "gov_api"
    MUNICIPAL_API = "municipal_api"
    SCRAPING = "scraping"
    EMAIL = "email"
    WEBHOOK = "webhook"


class SourceStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class TenderEventType(str, enum.Enum):
    SUBMISSION_DEADLINE = "submission_deadline"
    SITE_VISIT = "site_visit"
    QUESTIONS_DEADLINE = "questions_deadline"
    CLARIFICATION = "clarification"
    CANCELLATION = "cancellation"
    AMENDMENT = "amendment"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"


class ActionType(str, enum.Enum):
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"
    REJECTED = "rejected"
