"""
config/settings.py — הגדרות אפליקציה מבוססות Pydantic BaseSettings.

כל משתני הסביבה נטענים מקובץ .env. ניתן לגשת להגדרות דרך הסינגלטון `settings`.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any
from pydantic import field_validator, model_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel
    from dotenv import dotenv_values

    class SettingsConfigDict(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    class BaseSettings(BaseModel):  # type: ignore
        def __init__(self, **values):
            # טעינה אוטומטית מ-.env ומ-os.environ
            env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            file_vals = dotenv_values(env_file_path) if os.path.exists(env_file_path) else {}
            env_vals = {k.lower(): v for k, v in file_vals.items()}
            env_vals.update({k.lower(): v for k, v in os.environ.items()})
            merged = {**env_vals, **values}
            super().__init__(**merged)


class Settings(BaseSettings):
    """
    הגדרות ריצה של המערכת — נטענות מ-.env ומשתני סביבה.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Gemini AI
    # -------------------------------------------------------------------------
    gemini_api_key: str = ""

    # -------------------------------------------------------------------------
    # Supabase / Database
    # -------------------------------------------------------------------------
    supabase_url: str = "https://your-project.supabase.co"
    supabase_key: str = ""
    supabase_db_url: str = "sqlite:///leads_tenders.db"

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # -------------------------------------------------------------------------
    # SMTP / Email
    # -------------------------------------------------------------------------
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # -------------------------------------------------------------------------
    # Application / Business Logic
    # -------------------------------------------------------------------------
    contractor_profile_id: int = 1

    # נשמר כמחרוזת מופרדת בפסיקים ומפוענח ב-validator
    scan_times: list[str] = ["06:00", "12:00", "18:00"]

    fast_track_business_fit_threshold: int = 80
    fast_track_urgency_threshold: int = 70
    fast_track_confidence_threshold: float = 0.7

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------
    environment: str = "development"
    debug: bool = False
    secret_key: str = "change_me_in_production"

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------

    @field_validator("scan_times", mode="before")
    @classmethod
    def parse_scan_times(cls, v: Any) -> list[str]:
        """פרסור שעות סריקה ממחרוזת מופרדת בפסיקים."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            parts = [t.strip() for t in v.split(",") if t.strip()]
            for p in parts:
                if not re.match(r"^\d{2}:\d{2}$", p):
                    raise ValueError(f"פורמט שעה שגוי ב-scan_times: {p!r}, מצופה HH:MM")
            return parts
        raise ValueError("scan_times חייב להיות רשימה או מחרוזת מופרדת בפסיקים")

    @field_validator("fast_track_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"סף confidence חייב להיות בין 0.0 ל-1.0, התקבל: {v}")
        return v

    @model_validator(mode="after")
    def validate_thresholds(self) -> Settings:
        for attr in ("fast_track_business_fit_threshold", "fast_track_urgency_threshold"):
            val = getattr(self, attr)
            if not (0 <= val <= 100):
                raise ValueError(f"{attr} חייב להיות בין 0 ל-100, התקבל: {val}")
        return self

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def fast_track_config(self) -> dict[str, Any]:
        """מילון קונפיגורציית ספי ה-Fast-Track לשימוש ב-scorer וב-dispatcher."""
        return {
            "business_fit_threshold": self.fast_track_business_fit_threshold,
            "urgency_threshold": self.fast_track_urgency_threshold,
            "confidence_threshold": self.fast_track_confidence_threshold,
        }

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
