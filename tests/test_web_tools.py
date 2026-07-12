from pathlib import Path
import pytest
from src.tools.models import ToolRequest, ToolValidationError
from src.tools.web_factory import create_web_research_registry
from src.tools.web_models import SourceType, WebPage, WebSource
from src.tools.web_tools import CompareSourcesTool, OpenPageTool, WebSearchTool

class FakeSearch:
    async def search(self, query: str, *, limit: int):
        one = WebSource.retrieved("https://example.test/a", "A", source_type=SourceType.NEWS)
        duplicate = WebSource.retrieved("https://EXAMPLE.test/a/", "duplicate")
        return [one, duplicate][:limit]

class FakePages:
    async def open(self, url: str):
        source = WebSource.retrieved(url, "Page")
        return WebPage(source, "Evidence", "text/plain", 8)

@pytest.mark.asyncio
async def test_search_deduplicates_and_page_retains_provenance():
    search = WebSearchTool(FakeSearch()); search.validate({"query": "nexus"})
    result = await search.execute({"query": "nexus"})
    assert len(result["sources"]) == 1 and result["sources"][0]["retrieved_at"]
    page = await OpenPageTool(FakePages()).execute({"url": "https://example.test/a"})
    assert page["content"] == "Evidence" and page["source"]["url"].startswith("https://")

@pytest.mark.asyncio
async def test_comparison_rejects_fabricated_attribution():
    tool = CompareSourcesTool()
    sources = [{"url": "https://example.test/a", "title": "A"}]
    claims = [{"text": "Fact", "source_url": "https://other.test"}]
    with pytest.raises(ToolValidationError): tool.validate({"sources": sources, "claims": claims})
    claims[0]["source_url"] = sources[0]["url"]; tool.validate({"sources": sources, "claims": claims})
    result = await tool.execute({"sources": sources, "claims": claims})
    assert result["claims"][0]["citation"] == 1 and result["references"][0].startswith("[1]")

@pytest.mark.asyncio
async def test_multi_source_comparison_assigns_stable_citations():
    tool = CompareSourcesTool()
    sources = [{"url": "https://a.test", "title": "A"},
               {"url": "https://b.test", "title": "B"}]
    claims = [{"text": "One", "source_url": sources[0]["url"]},
              {"text": "Two", "source_url": sources[1]["url"]}]
    tool.validate({"sources": sources, "claims": claims})
    result = await tool.execute({"sources": sources, "claims": claims})
    assert [item["citation"] for item in result["claims"]] == [1, 2]

@pytest.mark.asyncio
async def test_external_access_and_note_writes_require_confirmation(tmp_path: Path):
    root = tmp_path / "notes"
    registry = create_web_research_registry(FakeSearch(), FakePages(), notes_root=root,
                                             audit_path=tmp_path / "audit.jsonl")
    search = await registry.invoke(ToolRequest("web.search", {"query": "x"}))
    assert search.error_code == "confirmation_required"
    note = ToolRequest("research.save_note", {"path": "report.md", "content": "# Sources"})
    denied = await registry.invoke(note); saved = await registry.invoke(note, confirmed=True)
    assert denied.error_code == "confirmation_required" and saved.success
    assert (root / "report.md").read_text() == "# Sources"
