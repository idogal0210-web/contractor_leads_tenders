"""
main.py — נקודת כניסה ראשית למערכת איתור ולכידת לידים ומכרזים.
מריץ את צינור האיתור, מעדכן את מאגר הנתונים ומייצר את הדשבורד הסטטי docs/index.html (Serverless).
"""
import os
import sys
import json
import webbrowser
from datetime import datetime
from core.db.session import get_sync_db, init_db
from core.db.models import Opportunity
from src.ui_builder import build_and_save_docs_app


def run_pipeline_and_refresh_dashboard(open_browser: bool = False):
    """
    1. אתחול מסד הנתונים במידת הצורך
    2. טעינת כל ההזדמנויות הפעילות
    3. שמירה בקובץ JSON מקומי (data/opportunities.json)
    4. בניית קובץ docs/index.html האינטראקטיבי
    """
    print("[*] מאתחל מסד נתונים ומבנה נתונים...")
    init_db()

    project_root = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    db = get_sync_db()
    try:
        opps = db.query(Opportunity).all()
        opps_data = [{c.name: getattr(o, c.name) for c in o.__table__.columns} for o in opps]

        # שמירה כ-JSON מקומי
        json_path = os.path.join(data_dir, "opportunities.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(opps_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"[+] נשמרו {len(opps_data)} הזדמנויות ב-data/opportunities.json")

        # בניית הדשבורד הסטטי האינטראקטיבי
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
