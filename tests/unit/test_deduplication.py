"""
בדיקות יחידה למנגנון מניעת כפילויות ו-Idempotency.
"""
from unittest.mock import MagicMock
from processors.deduplication import compute_content_hash, is_duplicate, get_existing_item


def test_compute_content_hash_consistency():
    """בדיקה שתוכן זהה מייצר תמיד את אותה חתימת SHA-256."""
    text1 = "עבודות אינסטלציה בבניין מגורים בתל אביב"
    text2 = "  עבודות אינסטלציה בבניין מגורים בתל אביב  "
    assert compute_content_hash(text1) == compute_content_hash(text2)


def test_compute_content_hash_difference():
    """בדיקה שתוכן שונה מייצר חתימות שונות."""
    text1 = "מכרז עיריית נתניה 1"
    text2 = "מכרז עיריית נתניה 2"
    assert compute_content_hash(text1) != compute_content_hash(text2)


def test_is_duplicate_returns_true_when_exists():
    """בדיקה שפריט קיים מזוהה ככפילות."""
    mock_db = MagicMock()
    mock_item = MagicMock(content_hash="mock_hash_123", id="uuid-123")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_item

    assert is_duplicate("mock_hash_123", mock_db) is True


def test_is_duplicate_returns_false_when_absent():
    """בדיקה שפריט חדש אינו מזוהה ככפילות."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    assert is_duplicate("new_hash_456", mock_db) is False
