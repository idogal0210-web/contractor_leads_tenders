"""
api/main_api.py — שרת קליטת לידים בזמן אמת (FastAPI).
מאפשר לקבל פניות ישירות ממערכות חיצוניות כמו Webhooks של WhatsApp (דרך Twilio למשל).
"""
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, BackgroundTasks, Form, HTTPException
from pydantic import BaseModel

# Add root directory to sys.path if running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db.session import SessionLocal
from main import process_lead_item, load_contractor_profile

app = FastAPI(title="Contractor Leads API", description="API לקליטת לידים לוואטסאפ")


class DirectLeadPayload(BaseModel):
    """מודל נתונים לקליטת ליד דרך API (JSON)"""
    content: str
    source_name: Optional[str] = "קליטה ישירה (API)"
    phone_number: Optional[str] = None


def background_process_lead(content: str, source_name: str):
    """פונקציית רקע המעבירה את ההודעה לצינור העיבוד הרגיל."""
    db = SessionLocal()
    try:
        profile = load_contractor_profile()
        
        raw_item = {
            "content": content,
            "title": f"ליד נכנס: {content[:30]}...",
            "source_name": source_name,
            "url": None,  # קליטה ישירה לרוב ללא לינק
            "source_label": f"{source_name} — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # מעביר את הליד למנגנון העיבוד המרכזי שכולל הזרקה ל-AI ושמירה
        process_lead_item(raw_item, db, profile)
        print(f"[API] ליד חדש עובד בהצלחה ממקור: {source_name}")
    except Exception as e:
        print(f"[API] שגיאה בעיבוד ליד רקע: {e}")
    finally:
        db.close()


@app.post("/api/whatsapp/incoming")
async def receive_whatsapp(
    background_tasks: BackgroundTasks, 
    Body: str = Form(None), 
    From: str = Form(None)
):
    """
    Webhook לקליטת הודעות WhatsApp.
    תואם לפורמט של Twilio (x-www-form-urlencoded).
    """
    if not Body:
        raise HTTPException(status_code=400, detail="No message body provided")
    
    sender = From or "WhatsApp לא ידוע"
    
    # שולח לעיבוד ברקע כדי להשיב מהר לשרת הוואטסאפ (למניעת Timeout)
    background_tasks.add_task(
        background_process_lead, 
        content=Body, 
        source_name=f"הודעת WhatsApp מ-{sender}"
    )
    
    return {"status": "received", "message": "הליד נקלט ומועבר לעיבוד ה-AI"}


@app.post("/api/leads/direct")
async def receive_direct_lead(payload: DirectLeadPayload, background_tasks: BackgroundTasks):
    """
    נקודת קליטה גנרית למערכות אחרות באמצעות JSON.
    """
    background_tasks.add_task(
        background_process_lead,
        content=payload.content,
        source_name=payload.source_name
    )
    return {"status": "received", "message": "Lead queued for processing"}


@app.get("/health")
def health_check():
    """בדיקת תקינות השרת"""
    return {"status": "ok", "service": "contractor-leads-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main_api:app", host="0.0.0.0", port=8000, reload=True)
