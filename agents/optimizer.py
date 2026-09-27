"""
agents/optimizer.py — Meta-Optimizer AI

מפעיל רפלקציה על החלטות ביטול (rejected) שהמשתמש עשה,
ומציע עדכונים ל-system_prompt ול-excluded_keywords כדי למנוע חיוביות כוזבות.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# כדי לוודא שניתן להריץ מתוך התיקייה הראשית
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import joinedload
from core.db.session import get_sync_db
from core.db.models import OpportunityAction, Opportunity, ActionType

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("google-genai is not installed. Please pip install google-genai.")
    sys.exit(1)


def fetch_rejected_leads(db) -> list[str]:
    """שולף את כל הלידים שסומנו כנדחים, בצירוף טקסט המקור שלהם."""
    actions = db.query(OpportunityAction).options(
        joinedload(OpportunityAction.opportunity).joinedload(Opportunity.source_item)
    ).filter(
        OpportunityAction.action_type.in_([ActionType.REJECTED, "permanently_deleted"])
    ).all()
    
    texts = []
    for action in actions:
        if action.opportunity and action.opportunity.source_item:
            texts.append(action.opportunity.source_item.raw_content)
            
    return texts


def dummy_validation(proposal: str) -> bool:
    """
    פונקציית ולידציה דמי שמוודאת שההצעה מכילה התייחסות לשדות המבוקשים.
    """
    if not proposal:
        return False
    if "excluded_keywords" in proposal.lower() or "system_prompt" in proposal.lower():
        return True
    return False


def main():
    load_dotenv()
    
    print("Fetching rejected leads from DB...")
    with get_sync_db() as db:
        rejected_texts = fetch_rejected_leads(db)
        
    if not rejected_texts:
        print("No rejected leads found to analyze.")
        # נמשיך כדוגמה במקרה שאין דאטה, רק בשביל ה-validation
        # return
        
    yaml_path = Path("config/lead_filtering_skill.yaml")
    if not yaml_path.exists():
        print(f"Could not find YAML at {yaml_path.resolve()}")
        return
        
    yaml_content = yaml_path.read_text(encoding="utf-8")
    rejected_leads_str = "\n---\n".join(rejected_texts[:20])
    
    if not rejected_texts:
         rejected_leads_str = "No rejected leads available right now. This is a dummy prompt test."
    
    prompt = f"""
    Here is the current skill YAML: 
    ```yaml
    {yaml_content}
    ```
    
    Here are leads the user REJECTED. The AI incorrectly thought they were good.
    ```text
    {rejected_leads_str}
    ```
    
    Analyze patterns and propose atomic edits to `excluded_keywords` or `system_prompt` to prevent these false positives.
    Return your response explaining the patterns, followed by the suggested YAML updates.
    """
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment. Please set it.")
        return
        
    print("Calling Gemini API (gemini-1.5-pro)...")
    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )
        suggestion = response.text
        print("\n=== OPTIMIZER SUGGESTION ===\n")
        print(suggestion)
        
        # Apply dummy validation
        if dummy_validation(suggestion):
            print("\n[✔] Suggestion passed dummy validation. (Could be automatically applied here)")
        else:
            print("\n[✖] Suggestion failed dummy validation.")
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")


if __name__ == "__main__":
    main()
