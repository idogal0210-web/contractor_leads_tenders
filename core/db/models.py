"""
מודלי מסד נתונים — מערכת ניהול לידים ומכרזים לקבלנים
SQLAlchemy 2.x declarative models with UUID primary keys and full relationship graph.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import JSON, Uuid as UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """מחלקת בסיס משותפת לכל המודלים."""
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OpportunityType(str, enum.Enum):
    """סוג ההזדמנות — מכרז או ליד."""
    TENDER = "tender"
    LEAD = "lead"


class OpportunityCategory(str, enum.Enum):
    """קטגוריית ההזדמנות לפי סוג הפרסום."""
    SERVICE_REQUEST = "service_request"
    PROVIDER_AD = "provider_ad"
    RECOMMENDATION_REQUEST = "recommendation_request"
    SUBCONTRACTING = "subcontracting"
    IRRELEVANT = "irrelevant"
    UNCERTAIN = "uncertain"


class MatchStatus(str, enum.Enum):
    """תוצאת התאמת ההזדמנות לפרופיל הקבלן."""
    FIT = "fit"
    NO_FIT = "no_fit"
    NEEDS_REVIEW = "needs_review"


class VerificationStatus(str, enum.Enum):
    """סטטוס אימות הנתונים שחולצו."""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    NEEDS_HUMAN = "needs_human"


class ProcessingStatus(str, enum.Enum):
    """סטטוס עיבוד פריט מקור."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class SourceType(str, enum.Enum):
    """סוג מקור הנתונים."""
    GOV_API = "gov_api"
    MUNICIPAL_API = "municipal_api"
    SCRAPING = "scraping"
    EMAIL = "email"
    WEBHOOK = "webhook"


class SourceStatus(str, enum.Enum):
    """סטטוס פעילות המקור."""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class TenderEventType(str, enum.Enum):
    """סוג אירוע במכרז."""
    SUBMISSION_DEADLINE = "submission_deadline"
    SITE_VISIT = "site_visit"
    QUESTIONS_DEADLINE = "questions_deadline"
    CLARIFICATION = "clarification"
    CANCELLATION = "cancellation"
    AMENDMENT = "amendment"


class NotificationChannel(str, enum.Enum):
    """ערוץ שליחת התראה."""
    EMAIL = "email"
    TELEGRAM = "telegram"


class ActionType(str, enum.Enum):
    """סוג פעולה שבוצעה על הזדמנות."""
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Model 1 — ContractorProfile
# ---------------------------------------------------------------------------

class ContractorProfile(Base):
    """
    פרופיל קבלן — הגדרת תחומי עיסוק, אזורי שירות ויכולות.
    משמש כבסיס להתאמת הזדמנויות.
    """

    __tablename__ = "contractor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    # אזור שירות גיאוגרפי — ברירת מחדל: כלל הארץ
    service_area: Mapped[str] = mapped_column(String, nullable=False, default="ארצי")
    # רשימת קודי ענף
    trades: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # ענפים מוחרגים
    excluded_trades: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # טווח ערך פרויקט — NULL = ללא הגבלה
    min_project_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_project_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # זמינות מתאריך
    available_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # סיווגי קבלן (ג', ב', א' וכד')
    classifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # תעודות ורישיונות
    certifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # יכולת ערבות בנקאית
    bond_capacity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # מילות מפתח בעברית לפי ענף: {trade_code: [keyword, ...]}
    trade_keywords_hebrew: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # קשרים
    opportunities: Mapped[list["Opportunity"]] = relationship(
        "Opportunity", back_populates="contractor_profile", lazy="select"
    )


# ---------------------------------------------------------------------------
# Model 2 — Source
# ---------------------------------------------------------------------------

class Source(Base):
    """
    מקור נתונים — מגדיר API, אתר גרידה או ערוץ כניסת מידע.
    כולל הגדרות תדירות סריקה וניטור שגיאות.
    """

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # שם ייחודי לזיהוי המקור
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    source_type: Mapped[SourceType] = mapped_column(String, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # שיטת אימות (api_key, oauth2, basic וכד')
    auth_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # תדירות סריקה בשעות
    scan_frequency_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_successful_scan_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[SourceStatus] = mapped_column(
        String, nullable=False, default=SourceStatus.ACTIVE
    )
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # עלות חודשית (לצורך ניתוח ROI)
    cost_per_month: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # קונפיגורציה ספציפית לאדפטר
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # קשרים
    items: Mapped[list["SourceItem"]] = relationship(
        "SourceItem", back_populates="source", lazy="select"
    )


# ---------------------------------------------------------------------------
# Model 3 — SourceItem
# ---------------------------------------------------------------------------

class SourceItem(Base):
    """
    פריט גולמי שנאסף ממקור — לפני עיבוד ועיצוב.
    ה-content_hash מונע כפילויות בקליטה.
    """

    __tablename__ = "source_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    # תוכן גולמי מקורי
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    # SHA-256 של התוכן — ייחודי לגילוי כפילויות
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # זמן גילוי על ידי המערכת
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    item_type: Mapped[Optional[OpportunityType]] = mapped_column(String, nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        String, nullable=False, default=ProcessingStatus.PENDING
    )
    processing_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # קשרים
    source: Mapped["Source"] = relationship("Source", back_populates="items")
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        "Opportunity", back_populates="source_item", uselist=False, lazy="select"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="source_item", lazy="select"
    )


# ---------------------------------------------------------------------------
# Model 4 — Document
# ---------------------------------------------------------------------------

class Document(Base):
    """
    מסמך מצורף לפריט מקור — קובץ PDF, Word וכד'.
    כולל תמיכה ב-OCR ואחסון טקסט מחולץ.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    # SHA-256 של הקובץ
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # נתיב בתוך ה-object storage (S3/Supabase Storage)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # טקסט שחולץ מהמסמך
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # האם בוצע OCR על המסמך
    ocr_performed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # קשרים
    source_item: Mapped["SourceItem"] = relationship(
        "SourceItem", back_populates="documents"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", lazy="select"
    )


# ---------------------------------------------------------------------------
# Model 5 — DocumentVersion
# ---------------------------------------------------------------------------

class DocumentVersion(Base):
    """
    גרסה של מסמך — עוקב אחר שינויים לאורך זמן.
    ה-UniqueConstraint מבטיח מספור גרסאות תקין לכל מסמך.
    """

    __tablename__ = "document_versions"

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # תיאור קצר של השינויים מהגרסה הקודמת
    diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # שדות שהשתנו (JSON)
    changed_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # קשרים
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    tender_events: Mapped[list["TenderEvent"]] = relationship(
        "TenderEvent", back_populates="document_version", lazy="select"
    )


# ---------------------------------------------------------------------------
# Model 6 — Opportunity
# ---------------------------------------------------------------------------

class Opportunity(Base):
    """
    הזדמנות עסקית — הרשומה המרכזית של המערכת.
    כולל שדות מחולצים עם ראיות ורמת ביטחון, ציון התאמה וסטטוסים.

    כלל ה-budget_value: NULL אם לא צוין מפורשות — אין לנחש!
    """

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # קשר ייחודי 1:1 לפריט מקור
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    opportunity_type: Mapped[OpportunityType] = mapped_column(String, nullable=False)
    category: Mapped[OpportunityCategory] = mapped_column(
        String, nullable=False, default=OpportunityCategory.UNCERTAIN
    )

    # ------------------------------------------------------------------
    # שדות מחולצים — כל שדה מלווה ראיה ורמת ביטחון (0.0–1.0)
    # ------------------------------------------------------------------

    # כותרת ההזדמנות
    title_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # מיקום גיאוגרפי
    location_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # תקציב — NULL אם לא צוין במפורש, אסור לנחש
    budget_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    budget_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # סוג עבודה / ענף
    work_type_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_type_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_type_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # מועד הגשה / תפוגה
    deadline_value: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # פרטי יצירת קשר
    contact_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contact_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # מספר מכרז (אם קיים)
    tender_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # שם הגוף המפרסם
    publisher_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # ------------------------------------------------------------------
    # ציונים (0–100)
    # ------------------------------------------------------------------

    # התאמה עסקית לפרופיל הקבלן
    score_business_fit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # דחיפות (קרבת deadline, מהירות ביצוע)
    score_urgency: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # ביטחון כולל באיכות הנתונים שחולצו
    score_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # האם מסלול מהיר (fast-track)
    is_fast_track: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ------------------------------------------------------------------
    # התאמה לפרופיל
    # ------------------------------------------------------------------

    match_status: Mapped[Optional[MatchStatus]] = mapped_column(String, nullable=True)
    match_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # פרופיל הקבלן שכנגדו בוצעה ההתאמה
    contractor_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contractor_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # מטא-נתונים
    # ------------------------------------------------------------------

    verification_status: Mapped[VerificationStatus] = mapped_column(
        String, nullable=False, default=VerificationStatus.UNVERIFIED
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # קשרים
    source_item: Mapped["SourceItem"] = relationship(
        "SourceItem", back_populates="opportunity"
    )
    contractor_profile: Mapped[Optional["ContractorProfile"]] = relationship(
        "ContractorProfile", back_populates="opportunities"
    )
    tender_events: Mapped[list["TenderEvent"]] = relationship(
        "TenderEvent", back_populates="opportunity", lazy="select"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="opportunity", lazy="select"
    )
    actions: Mapped[list["OpportunityAction"]] = relationship(
        "OpportunityAction", back_populates="opportunity", lazy="select"
    )


# ---------------------------------------------------------------------------
# Model 7 — TenderEvent
# ---------------------------------------------------------------------------

class TenderEvent(Base):
    """
    אירוע הקשור למכרז — deadline, ביקור אתר, הבהרה וכד'.
    stable_calendar_event_id מאפשר עדכון אירוע קיים בלוח שנה.
    """

    __tablename__ = "tender_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[TenderEventType] = mapped_column(String, nullable=False)
    event_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # מזהה יציב לעדכון אירוע בלוח שנה (Google Calendar וכד')
    stable_calendar_event_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # גרסת המסמך שממנה חולץ האירוע
    document_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # קשרים
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity", back_populates="tender_events"
    )
    document_version: Mapped[Optional["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="tender_events"
    )


# ---------------------------------------------------------------------------
# Model 8 — Notification
# ---------------------------------------------------------------------------

class Notification(Base):
    """
    התראה שנשלחה (או ממתינה) על הזדמנות — אימייל או טלגרם.
    opportunity_version_snapshot שומר snapshot של הנתונים בעת השליחה.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(String, nullable=False)
    # כתובת מייל / chat_id בטלגרם
    recipient: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    body_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # pending / sent / failed
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_detail: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # snapshot של נתוני ההזדמנות בעת השליחה (לאודיט)
    opportunity_version_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # קשרים
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity", back_populates="notifications"
    )


# ---------------------------------------------------------------------------
# Model 9 — OpportunityAction
# ---------------------------------------------------------------------------

class OpportunityAction(Base):
    """
    פעולה שבוצעה על הזדמנות — לוג ביקורת (audit log) של מעקב מכרז.
    """

    __tablename__ = "opportunity_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[ActionType] = mapped_column(String, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # שם המשתמש / תהליך שביצע את הפעולה
    acted_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # זמן הפעולה — server default מאפשר שמירה ללא ציון מפורש
    acted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # קשרים
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity", back_populates="actions"
    )
