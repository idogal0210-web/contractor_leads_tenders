"""
core/db — ייצוא מרכזי של Base, מודלים וכל ה-enums.
ייבוא ממודול זה מבטיח רישום כל הטבלאות ב-metadata של Base.
"""
from core.db.enums import (
    ActionType,
    MatchStatus,
    NotificationChannel,
    OpportunityCategory,
    OpportunityType,
    ProcessingStatus,
    SourceStatus,
    SourceType,
    TenderEventType,
    VerificationStatus,
)

try:
    from core.db.models import (
        Base,
        ContractorProfile,
        Document,
        DocumentVersion,
        Notification,
        Opportunity,
        OpportunityAction,
        Source,
        SourceItem,
        TenderEvent,
    )
except ImportError:
    Base = None
    ContractorProfile = None
    Document = None
    DocumentVersion = None
    Notification = None
    Opportunity = None
    OpportunityAction = None
    Source = None
    SourceItem = None
    TenderEvent = None

__all__ = [
    "ActionType",
    "MatchStatus",
    "NotificationChannel",
    "OpportunityCategory",
    "OpportunityType",
    "ProcessingStatus",
    "SourceStatus",
    "SourceType",
    "TenderEventType",
    "VerificationStatus",
    "Base",
    "ContractorProfile",
    "Document",
    "DocumentVersion",
    "Notification",
    "Opportunity",
    "OpportunityAction",
    "Source",
    "SourceItem",
    "TenderEvent",
]
