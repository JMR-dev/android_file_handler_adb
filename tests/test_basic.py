"""Simple test to verify pytest setup."""

def test_basic():
    """Basic test to verify pytest is working."""
    assert 1 + 1 == 2


def test_imports():
    """Test that we can import our modules."""
    try:
        from src.utils.file_deduplication import FileDeduplicator
        deduplicator = FileDeduplicator()
        assert deduplicator is not None
    except ImportError as e:
        pytest.fail(f"Failed to import FileDeduplicator: {e}")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])