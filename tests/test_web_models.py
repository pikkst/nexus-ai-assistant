from datetime import datetime, timezone

from src.tools.web_models import SourceType, WebSource, citation, unique_sources


def test_sources_retain_provenance_and_citations() -> None:
    published = datetime(2026, 7, 1, tzinfo=timezone.utc)
    source = WebSource.retrieved(
        "https://example.test/story", "Example story",
        source_type=SourceType.NEWS, published_at=published, excerpt="Evidence",
    )
    assert source.retrieved_at.tzinfo is timezone.utc
    assert source.source_type is SourceType.NEWS
    assert citation(source, 1) == "[1] Example story (2026-07-01) — https://example.test/story"


def test_duplicate_urls_keep_first_seen_source() -> None:
    first = WebSource.retrieved("https://example.test/page/", "First")
    duplicate = WebSource.retrieved("https://EXAMPLE.test/page", "Duplicate")
    assert unique_sources([first, duplicate]) == [first]
