from codex.news_pipeline.sanitize import filter_trusted


def test_trusted_sources_filter():
    items = [
        {"source": {"handle": "@CoinDesk", "followers": 100000}},
        {"source": {"handle": "@random", "followers": 10}},
    ]
    trusted = filter_trusted(items, whitelist={"@CoinDesk"}, min_followers=50000)
    assert len(trusted) == 1
    assert trusted[0]["source"]["handle"] == "@CoinDesk"
