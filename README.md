# מערכת איתור ולכידת לידים ומכרזים לקבלנים (Contractor Leads & Tenders Engine)
**ליבת ניהול הזדמנויות עסקיות עבור קבלנים — Antigravity 2.0**

---

<div dir="rtl" style="text-align: right;">

## 🎯 מטרת המערכת
מערכת מודולרית ואוטונומית לאיתור, חילוץ, אימות, סיווג, ניקוד והפצה של הזדמנויות עסקיות לקבלנים.
המערכת פועלת בשני ערוצים מקבילים בעלי לוגיקה עסקית שונה:
1. **לידים פרטיים (איתותי ביקוש):** מיקוד בטריות, מהירות תגובה ומסלול מהיר (**Fast-Track**).
2. **מכרזים ציבוריים:** מיקוד בדיוק, שלמות עובדתית, מעקב גרסאות מסמכים, וניהול אירועי יומן (סיורי קבלנים, שאלות הבהרה, מועדי הגשה).

---

## 🏗️ ארכיטקטורת המערכת וה-Pipeline

```
[מקורות מידע: gov.il, עיריות, סקרייפרים, מיילים, Webhooks]
                           │
                           ▼
          [Adapters: איסוף ובידוד שגיאות]
                           │
                           ▼
        [Deduplication: מניעת כפילויות SHA-256]
                           │
                           ▼
            [OCR: pdfplumber + Tesseract]
                           │
                           ▼
      [LLM Extractor: Gemini 3.8 Flash (עובדות בלבד)]
                           │
                           ▼
        [Classifier: 6 קטגוריות לא-בינאריות]
                           │
                           ▼
       [Scorer: 3 מדדים נפרדים + Fast-Track]
                           │
                           ▼
  [Matcher: השוואה לפרופיל קבלן (FIT / NO_FIT / REVIEW)]
                           │
                           ▼
[Rule-Based Dispatcher: החלטת הפצה בקוד ללא LLM]
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
   [Email Alert (SMTP)]        [Telegram Bot Alert]
            │                             │
            └──────────────┬──────────────┘
                           ▼
       [Dashboard HTMX / Supabase PostgreSQL DB]
```

---

## ⚡ תכונות מפתח

* **LLM לחילוץ עובדות בלבד:** מופעל באמצעות `gemini-3.8-flash` ו-`google-genai` SDK. חוק ברזל: אם שדה (כמו תקציב) לא נכתב במפורש בטקסט — מוחזר `null` מוחלט ללא ניחושים.
* **אבטחת קלט לא מהימן (Guardrails):** טקסט חיצוני אינו מורשה להפעיל כלים או לשנות לוגיקת סוכן, ומנוטר נגד Prompt Injection.
* **הפרדת סמכויות והחלטות הפצה:** ה-LLM אך ורק מחלץ נתונים. ההחלטה האם לשלוח התראה מתבצעת **אך ורק על ידי חוקים דטרמיניסטיים מפורשים בקוד**.
* **מסלול מהיר (Fast-Track):** התראות דחופות בעלות התאמה גבוהה וטריות עוקפות את חלונות התזמון ונשלחות באופן מיידי.
* **מעקב גרסאות מסמכים:** מעקב שינויי הבהרות, דחיות ומועדי סיור לפי מזהה יציב (`stable_calendar_event_id`).
* **דוחות יומיים:** מופקים אוטומטית, נשמרים מקומית בדיסק ב-`reports/output/`, נשלחים בדוא"ל ובטלגרם, ומוצגים בדשבורד.

---

## 🚀 התקנה והרצה מהירה (Quick Start)

### 1. דרישות מוקדמות
* Python 3.12+
* Docker & Docker Compose
* מפתח API של Google Gemini (`gemini-3.8-flash`)
* מסד נתונים Supabase (PostgreSQL)

### 2. הגדרת משתני סביבה
העתק את קובץ הדוגמה והגדר את המפתחות:
```bash
cp .env.example .env
```
ערוך את קובץ `.env` והזן את הערכים:
* `GEMINI_API_KEY`: מפתח ה-API שלך מ-Google AI Studio
* `SUPABASE_DB_URL`: מחרוזת החיבור ל-PostgreSQL ב-Supabase
* `REDIS_URL`: כתובת שרת ה-Redis (`redis://localhost:6379/0`)
* `TELEGRAM_BOT_TOKEN` ו-`TELEGRAM_CHAT_ID`: עבור התראות לטלגרם
* `SMTP_*`: עבור שליחת מיילים

### 3. הרצה מקומית עם Docker Compose
המערכת כוללת תצורת Docker מלאה המריצה Redis, שרת FastAPI, Celery Worker ו-Celery Beat:
```bash
docker-compose up --build -d
```

### 4. החלת סכמת ה-DB (Alembic)
```bash
alembic upgrade head
```

### 5. גישה לממשק
פתח את הדפדפן בכתובת:
* **מסך בדיקה מהירה (Dashboard):** [http://localhost:8000](http://localhost:8000)
* **תיעוד API אינטראקטיבי (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 הרצת בדיקות (Automated Tests)
המערכת כוללת חבילת בדיקות יחידה ואינטגרציה מלאה:
```bash
pytest -v
```

---

## 📁 מבנה הספריות

```
איתור ולכידת לידים/
├── .env.example                # תבנית משתני סביבה
├── docker-compose.yml          # הרצת Redis + FastAPI + Celery
├── requirements.txt            # ספריות פייתון
├── alembic.ini                 # הגדרות Alembic
├── alembic/                    # קבצי מיגרציות למסד הנתונים
├── config/
│   ├── settings.py             # הגדרות מערכת (Pydantic BaseSettings)
│   └── contractor_profile.json # פרופיל קבלן יעד (מקצועות, אזור, מילות מפתח)
├── core/
│   ├── db/
│   │   ├── models.py           # 9 מודלים ב-SQLAlchemy 2.x
│   │   └── session.py          # חיבורי סשן סינכרוניים ואסינכרוניים
│   ├── queue/
│   │   ├── celery_app.py       # הגדרת Celery ו-Beat Schedule
│   │   └── tasks.py            # משימות רקע ו-Pipeline מלא
│   └── security/
│       └── guardrails.py       # סינון קלט לא מהימן וניטרול הזרקות
├── adapters/                   # מתאמי מקורות נתונים
│   ├── base.py                 # ממשק אבסטרקטי ומבנה RawItem/FetchResult
│   ├── gov_tenders.py          # API מכרזי ממשלה רשמי
│   ├── data_gov.py             # API מאגרי מידע מוניציפליים
│   ├── municipal_scraper.py    # סקרייפר Playwright לעיריות
│   ├── yad2_scraper.py         # סקרייפר לידים פרטיים ולוחות
│   └── email_ingestion.py      # קליטת לידים מתיבת מייל (IMAP)
├── processors/                 # מנועי עיבוד וניתוח
│   ├── deduplication.py        # מניעת כפילויות מבוססת SHA-256
│   ├── ocr.py                  # חילוץ טקסט חכם (pdfplumber + Tesseract)
│   ├── llm_extractor.py        # חילוץ עובדות מובנה באמצעות Gemini 3.8 Flash
│   ├── classifier.py           # סיווג ל-6 קטגוריות
│   ├── scorer.py               # ניקוד 3-מדדים וזיהוי Fast-Track
│   └── matcher.py              # התאמה והשוואה לפרופיל הקבלן
├── notifications/              # מנוע הפצה
│   ├── dispatcher.py           # מנוע שיגור מבוסס כללים דטרמיניסטיים
│   ├── email_sender.py         # שליחת דוא"ל דרך SMTP
│   ├── telegram_sender.py      # שליחת התראות לטלגרם
│   └── templates/              # תבניות HTML מעוצבות בעברית (RTL)
├── api/                        # שרת ה-Web וה-API
│   ├── main.py                 # אפליקציית FastAPI ראשית
│   ├── routes/                 # נתיבי Webhooks, הזדמנויות ודוחות
│   └── templates/              # דפי הדשבורד ב-HTML/HTMX (RTL)
├── reports/
│   ├── daily_report.py         # הפקה ושמירה מקומית של הדוח היומי
│   └── output/                 # שמירת עותקי דוחות מקומיים לפי תאריך
└── tests/                      # בדיקות יחידה ואינטגרציה
```

</div>
