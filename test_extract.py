import asyncio
from processors.llm_extractor import extract_opportunity

async def main():
    text = "ברוכים הבאים לטופ שיפוצים! הפורטל המקיף בישראל להשוואת הצעות מחיר מקבלנים."
    res = await extract_opportunity(text)
    print("opportunity_type:", res.opportunity_type)
    print("is_current:", res.is_current)
    print("title:", res.title.value)

asyncio.run(main())
