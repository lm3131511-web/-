from codex.config.models import SanitizerConfig
from codex.news_pipeline.sanitize import sanitize_items


def test_sanitize_removes_urls_and_mentions():
    config = SanitizerConfig(max_chars=50, strip_urls=True, strip_mentions=True)
    items = [
        {"body": "Breaking! https://example.com @user"},
    ]
    sanitized = sanitize_items(items, config)
    assert sanitized[0]["body"] == "Breaking!"
