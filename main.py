"""
main.py — נקודת כניסה ראשית למערכת איתור ולכידת לידים ומכרזים לקבלנים.
מריץ סריקה חיה, סינון ומניעת כפילויות, חילוץ עובדתי ב-Gemini AI,
שיגור התראות מיידיות למסלול מהיר (Fast-Track), ובניית הדשבורד האינטראקטיבי docs/index.html.
"""
import os
import sys
import json
import uuid
import asyncio
import webbrowser
from datetime import datetime, timezone, timedelta

from config.settings import settings
from core.db.session import get_sync_db, init_db
from core.db.models import Opportunity, Source, SourceItem, ProcessingStatus, FreshnessStatus
from processors.deduplication import compute_content_hash, is_duplicate
from processors.llm_extractor import extract_opportunity
from processors.classifier import classify_opportunity
from processors.scorer import score_opportunity
from processors.matcher import match_to_profile
from notifications.email_sender import _send_smtp_sync
from src.ui_builder import build_and_save_docs_app
from src.fetchers import fetch_live_web_leads


def _load_contractor_profile() -> dict:
    """טעינת פרופיל הקבלן והגדרות הענפים."""
    profile_path = os.path.join(os.path.dirname(__file__), "config", "contractor_profile.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "service_area": "ארצי",
        "trade_keywords_hebrew": {},
        "excluded_trades": [],
        "min_project_value": None,
        "max_project_value": None,
    }


def process_lead_item(raw_item: dict, db, profile: dict):
    """עיבוד ליד יחיד דרך כל שלבי הצינור."""
    content = raw_item.get("content", "").strip()
    if not content or len(content) < 15:
        return None

    content_hash = compute_content_hash(content)
    if is_duplicate(content_hash, db):
        return None

    # חילוץ מובנה בעזרת Gemini AI
    try:
        extracted = asyncio.run(extract_opportunity(content))
    except Exception as exc:
        print(f"[-] AI extraction error: {exc}")
        return None

    # בדיקת אקטואליות AI — אם Gemini קבע שהתוכן לא אקטואלי, דילוג
    if not extracted.is_current:
        print(f"[-] ליד נפסל (לא אקטואלי לפי AI): {extracted.title.value or content[:40]}")
        return None

    # חילוץ תאריך פרסום — מהפיצ'ר או מ-AI
    published_at_dt = None
    if raw_item.get("published_at"):
        try:
            published_at_dt = datetime.fromisoformat(str(raw_item["published_at"]).replace("Z", "+00:00"))
        except Exception:
            pass
    if not published_at_dt and extracted.estimated_publish_date:
        try:
            published_at_dt = datetime.fromisoformat(str(extracted.estimated_publish_date).replace("Z", "+00:00"))
            if published_at_dt.tzinfo is None:
                published_at_dt = published_at_dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # Freshness Gate — פסילת לידים ישנים מ-45 יום
    FRESHNESS_DAYS = 45
    if published_at_dt:
        if published_at_dt.tzinfo is None:
            published_at_dt = published_at_dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - published_at_dt
        if age > timedelta(days=FRESHNESS_DAYS):
            print(f"[-] ליד נפסל (ישן מ-{FRESHNESS_DAYS} יום): {extracted.title.value or content[:40]}")
            return None

    # בניית source_label
    source_name = raw_item.get("source_name", "מקור פתוח")
    source_label = raw_item.get("source_label")
    if not source_label:
        date_str = published_at_dt.strftime("%d/%m/%Y") if published_at_dt else datetime.now(timezone.utc).strftime("%d/%m/%Y")
        source_label = f"{source_name} — {date_str}"

    category, _ = classify_opportunity(extracted, content)
    score = score_opportunity(extracted, profile, settings.fast_track_config)
    match_res = match_to_profile(extracted, profile, score)

    deadline_dt = None
    if extracted.deadline.value:
        try:
            deadline_dt = datetime.fromisoformat(str(extracted.deadline.value).replace("Z", "+00:00"))
        except Exception:
            deadline_dt = None

    source_rec = db.query(Source).first()
    source_id = source_rec.id if source_rec else uuid.uuid4()

    source_item = SourceItem(
        id=uuid.uuid4(),
        source_id=source_id,
        raw_content=content,
        content_hash=content_hash,
        url=raw_item.get("url"),
        item_type=extracted.opportunity_type or "lead",
        processing_status=ProcessingStatus.DONE
    )
    db.add(source_item)
    db.commit()

    opp = Opportunity(
        id=uuid.uuid4(),
        source_item_id=source_item.id,
        opportunity_type=extracted.opportunity_type or "lead",
        category=category,
        title_value=extracted.title.value or raw_item.get("title", "ליד חדש"),
        title_evidence=extracted.title.evidence_text or content[:200],
        title_confidence=extracted.title.confidence or 0.8,
        location_value=extracted.location.value or "ארצי",
        location_evidence=extracted.location.evidence_text,
        location_confidence=extracted.location.confidence or 0.8,
        budget_value=extracted.budget.value,
        budget_currency=extracted.budget_currency or "ILS",
        budget_evidence=extracted.budget.evidence_text,
        budget_confidence=extracted.budget.confidence or 0.0,
        work_type_value=extracted.work_type.value or "שיפוץ כללי",
        work_type_evidence=extracted.work_type.evidence_text,
        work_type_confidence=extracted.work_type.confidence or 0.8,
        deadline_value=deadline_dt,
        deadline_evidence=extracted.deadline.evidence_text,
        deadline_confidence=extracted.deadline.confidence or 0.0,
        contact_value=extracted.contact.value,
        contact_evidence=extracted.contact.evidence_text,
        contact_confidence=extracted.contact.confidence or 0.8,
        tender_number=extracted.tender_number,
        publisher_name=raw_item.get("source_name", "מקור פתוח"),
        score_business_fit=score.business_fit,
        score_urgency=score.urgency,
        score_confidence=score.confidence,
        is_fast_track=score.is_fast_track,
        match_status=match_res.status,
        match_reason=match_res.reason,
        source_label=source_label,
        published_at=published_at_dt,
        freshness_status=FreshnessStatus.FRESH,
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)

    # שיגור התראה מיידית למייל אם הליד הוא מסלול מהיר 🔴
    if opp.is_fast_track:
        budget_str = f"{opp.budget_value} ₪" if opp.budget_value else "לא צוין"
        subject = f"[מסלול מהיר 🔴] ליד חדש לקבלן: {opp.title_value}"
        body = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; background: #0F1115; color: #F1F5F9; padding: 25px; border-radius: 12px; border: 1px solid #EA580C;">
            <h2 style="color: #EA580C; margin-top: 0;">התראת מסלול מהיר: זוהתה הזדמנות עסקית בדחיפות גבוהה</h2>
            <div style="background: #161920; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <p><strong>כותרת:</strong> {opp.title_value}</p>
                <p><strong>ענף:</strong> {opp.work_type_value}</p>
                <p><strong>מיקום:</strong> {opp.location_value}</p>
                <p><strong>תקציב:</strong> {budget_str}</p>
                <p><strong>איש קשר / טלפון:</strong> {opp.contact_value or 'בטקסט המקורי'}</p>
                <p><strong>ציון התאמה:</strong> {opp.score_business_fit}/100</p>
            </div>
            <p><strong>ציטוט עובדתי מהמקור:</strong><br/><i>"{opp.title_evidence}"</i></p>
            <hr style="border-color: #252B36; margin: 20px 0;"/>
            <p style="font-size: 11px; color: #94A3B8;">נשלח אוטומטית ממערכת ConstructLeads.ai</p>
        </div>
        """
        _send_smtp_sync(
            to=settings.smtp_from or "idogal0210@gmail.com",
            subject=subject,
            html_body=body
        )
        print(f"[!] נשלחה התראת מייל מיידית על ליד במסלול מהיר: {opp.title_value}")

        # שיגור התראת טלגרם מיידית
        if settings.telegram_bot_token and settings.telegram_chat_id:
            try:
                import httpx
                tg_text = (
                    f"🔴 <b>מסלול מהיר: זוהה ליד חדש לקבלן!</b>\\n\\n"
                    f"📌 <b>כותרת:</b> {opp.title_value}\\n"
                    f"🛠️ <b>ענף:</b> {opp.work_type_value}\\n"
                    f"📍 <b>מיקום:</b> {opp.location_value}\\n"
                    f"💰 <b>תקציב:</b> {budget_str}\\n"
                    f"📞 <b>טלפון/איש קשר:</b> {opp.contact_value or 'בטקסט המקורי'}\\n"
                    f"📊 <b>ציון התאמה:</b> {opp.score_business_fit}/100\\n\\n"
                    f"<i>ציטוט מהמקור:</i>\\n\"{opp.title_evidence}\""
                )
                httpx.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": settings.telegram_chat_id, "text": tg_text, "parse_mode": "HTML"},
                    timeout=10
                )
                print(f"[!] נשלחה התראת טלגרם מיידית: {opp.title_value}")
            except Exception as tg_err:
                print(f"[-] Telegram alert error: {tg_err}")

    return opp


def run_pipeline_and_refresh_dashboard(open_browser: bool = False):
    """הרצת הצינור המלא ועדכון הדשבורד."""
    print("[*] מאתחל מסד נתונים ומבנה נתונים...")
    init_db()

    project_root = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    profile = _load_contractor_profile()

    db = get_sync_db()
    try:
        # 1. סריקת מקורות רשת חיים
        print("[*] סורק מקורות רשת חיים...")
        live_items = fetch_live_web_leads()
        
        # סריקת מכרזים حكومיים (Gov RSS)
        from src.fetchers import fetch_gov_tenders
        live_items.extend(fetch_gov_tenders())
        
        # סריקת דפדפן חכמה (Playwright) — לוחות דרושים ופייסבוק
        try:
            from src.playwright_scrapers import fetch_job_boards, fetch_facebook_groups
            live_items.extend(fetch_job_boards())
            live_items.extend(fetch_facebook_groups())
        except ImportError:
            print("[-] Playwright scrapers not available.")

        new_leads_count = 0
        for item in live_items:
            processed = process_lead_item(item, db, profile)
            if processed:
                new_leads_count += 1
        if new_leads_count > 0:
            print(f"[+] נוספו {new_leads_count} לידים חדשים ומאומתים למאגר")

        # 2. טעינת כל ההזדמנויות
        opps = db.query(Opportunity).all()
        
        # 3. אימות כתובות URL (Parallel Check)
        from src.validation import validate_opportunities_batch
        from core.db.models import UrlValidationStatus
        print("[*] מאמת כתובות URL של ההזדמנויות...")
        validate_opportunities_batch(opps)
        db.commit()

        opps_data = []
        for o in opps:
            d = {c.name: getattr(o, c.name) for c in o.__table__.columns}
            if hasattr(o, "source_item") and o.source_item and o.source_item.url:
                d["url"] = o.source_item.url
            opps_data.append(d)

        # 4. שמירה כ-JSON מקומי
        json_path = os.path.join(data_dir, "opportunities.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(opps_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"[+] סונכרנו {len(opps_data)} הזדמנויות לקובץ: {json_path}")

        # 4. בניית הדשבורד הסטטי האינטראקטיבי
        html_file = build_and_save_docs_app(opps_data, project_root)
        print(f"[SUCCESS] הדשבורד מוכן בכתובת: {html_file}")

        if open_browser:
            webbrowser.open(f"file://{os.path.abspath(html_file)}")

        return html_file
    finally:
        db.close()


if __name__ == "__main__":
    should_open = "--open" in sys.argv
    run_pipeline_and_refresh_dashboard(open_browser=should_open)
