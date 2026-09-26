<div dir="rtl">

# ConstructLeads.ai — מערכת איתור לידים ומכרזים לקבלנים

> מערכת מודיעין עסקי אוטומטית, מבוססת AI, לאיתור ולכידת הזדמנויות עבודה ומכרזים בענף הבנייה והשיפוצים בישראל.  
> מקורות המידע הם **מקורות אמת בלבד** — ממשלה, פורטלים מוסמכים, ורשתות חברתיות רלוונטיות.

---

## 🏗️ ארכיטקטורת 3 מנועי לידים

### שכבה 1 — מקורות האמת

| מנוע | מקור | שיטה | קובץ |
|------|------|-------|------|
| **B2G** — מכרזים ממשלתיים | [data.gov.il](https://data.gov.il) — מנהל הרכש | HTTP Direct API (M2M) | `src/fetchers.py` |
| **B2B** — לוחות פרויקטים | [tenders.co.il](https://tenders.co.il) (יפעת) — בינוי + עבודות עפר | Authenticated DOM Parsing (Playwright) | `src/b2b_authenticated.py` |
| **B2C** — לידים פרטיים | קבוצות פייסבוק — שיפוצים ובנייה | Apify Cloud Scraper (Polling) | `src/apify_fetcher.py` |

### שכבה 2 — עוקף חומות תשלום

כאשר מכרז נשלף מלוח סגור (יפעת), המערכת מחפשת אוטומטית את עמוד המקור הפתוח (אתר עירייה/מועצה) ומחליפה את הקישור לפני הצגה בדשבורד.

**קובץ:** `src/source_resolver.py`

### שכבה 3 — עיבוד AI (Two-Tier)

```
[כל ליד נכנס]
       │
       ▼
[Tier 1 - Bouncer: gemini-1.5-flash]
  is_valid_lead_intent()  ← זבל? → 🗑️ נזרק
       │ כוונה אמיתית
       ▼
[Tier 2 - Closer: gemini-3.8-pro]
  extract_opportunity()   ← חילוץ עובדתי מדויק
       │
       ▼
[Classifier + Scorer + Matcher]
       │
       ▼
[Dashboard + Supabase DB]
```

---

## ⚡ עקרונות ברזל

1. **אפס ניחושים:** אם שדה (כמו תקציב) לא נכתב במפורש בטקסט — מוחזר `null`. לעולם לא 0, לעולם לא "לא ידוע".
2. **מקורות אמת בלבד:** אין חיפוש גוגל חופשי, אין מילות מפתח אקראיות. כל ליד מגיע ממקור מוסמך ומאומת.
3. **ה-LLM אינו מחליט על הפצה:** ההחלטה האם לשלוח התראה נקבעת אך ורק על ידי חוקים דטרמיניסטיים (`notifications/dispatcher.py`).
4. **Guardrails:** כל טקסט חיצוני עובר `wrap_as_untrusted()` לפני העברה ל-AI.

---

## 🚀 הרצה מהירה

### דרישות
- Python 3.12+
- חשבון Supabase (PostgreSQL)
- מפתח Gemini API
- מפתח Apify API

### הגדרה
```bash
cp .env.example .env
# ערוך את .env עם המפתחות שלך
python3 main.py
```

### משתני סביבה חובה
| משתנה | תיאור |
|--------|--------|
| `GEMINI_API_KEY` | מפתח Google AI Studio |
| `SUPABASE_URL` | כתובת פרויקט Supabase |
| `SUPABASE_KEY` | מפתח Supabase Anon |
| `SUPABASE_DB_URL` | מחרוזת PostgreSQL ישירה |
| `APIFY_API_TOKEN` | מפתח Apify (לסריקת פייסבוק) |
| `APIFY_FACEBOOK_TASK_ID` | מזהה המשימה ב-Apify (`8dHQotGhHR7FuEnfU`) |
| `TAVILY_API_KEY` | לאיתור מקורות ציבוריים חלופיים |

---

## 🤖 GitHub Actions

הסריקה רצה **אך ורק בהפעלה ידנית** — אין תזמון אוטומטי פעיל.

להפעלה ידנית:  
`GitHub → Actions → Contractor Leads 24/7 Agent → Run workflow`

---

## 📁 מבנה הפרויקט

```
.
├── main.py                      # נקודת הכניסה הראשית — pipeline מלא
├── src/
│   ├── fetchers.py              # B2G: data.gov.il API (M2M)
│   ├── b2b_authenticated.py     # B2B: Playwright DOM scraper (יפעת)
│   ├── apify_fetcher.py         # B2C: Apify Facebook polling
│   ├── source_resolver.py       # עוקף חומות תשלום (Tavily search)
│   └── ui_builder.py            # מחולל HTML Dashboard
├── processors/
│   ├── llm_extractor.py         # Two-Tier AI (Flash + Pro)
│   ├── classifier.py            # סיווג 6 קטגוריות
│   ├── scorer.py                # ניקוד: business_fit, urgency, confidence
│   ├── matcher.py               # השוואה לפרופיל קבלן
│   └── deduplication.py         # מניעת כפילויות SHA-256
├── core/
│   ├── db/
│   │   ├── models.py            # 9 מודלי SQLAlchemy
│   │   └── session.py           # חיבור Supabase
│   └── security/
│       └── guardrails.py        # הגנה מפני Prompt Injection
├── notifications/
│   ├── dispatcher.py            # Rule-based — ללא LLM
│   ├── email_sender.py          # SMTP
│   └── telegram_sender.py      # Telegram Bot API
├── config/
│   ├── settings.py              # Pydantic BaseSettings
│   └── contractor_profile.json  # פרופיל הקבלן (מקצועות, אזורים)
├── docs/
│   └── index.html               # Dashboard סטטי (נבנה אוטומטית)
├── data/
│   └── opportunities.json       # snapshot עדכני (נבנה אוטומטית)
└── .github/
    └── workflows/
        └── agent_run.yml        # GitHub Actions — הפעלה ידנית בלבד
```

---

## 🔒 אבטחה

- **Secrets** מאוחסנים ב-GitHub Secrets בלבד — לא ב-code, לא ב-`.env` המועלה
- **Prompt Injection** — כל קלט חיצוני עטוף ב-`<untrusted_content>` לפני שליחה ל-Gemini
- **Token** של Apify ו-GitHub לא מופיעים בשום מקום בקוד

</div>
