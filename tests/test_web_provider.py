import httpx
import pytest
from src.tools.models import ToolError, ToolValidationError
from src.tools.web_provider import HttpPageProvider
from src.tools.web_security import validate_public_url

class Robots:
    def __init__(self, allowed=True): self.value = allowed
    async def allowed(self, url: str, user_agent: str) -> bool: return self.value

@pytest.mark.parametrize("url", ["file:///secret", "http://localhost/a", "http://127.0.0.1/a",
                                  "http://169.254.169.254/latest", "https://user@example.test"])
def test_unsafe_urls_are_rejected(url):
    with pytest.raises(ToolValidationError): validate_public_url(url)

@pytest.mark.asyncio
async def test_html_extraction_and_content_limit():
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, headers={"content-type": "text/html"}, content=b"<title>T</title><p>Hello</p>"))
    async with httpx.AsyncClient(transport=transport) as client:
        page = await HttpPageProvider(client, robots=Robots()).open("https://example.test")
        assert page.source.title == "T" and "Hello" in page.content
        with pytest.raises(ToolError) as error:
            await HttpPageProvider(client, robots=Robots(), max_bytes=2).open("https://example.test")
        assert error.value.code == "content_too_large"

@pytest.mark.asyncio
async def test_robots_formats_and_redirect_limits():
    redirect = httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "/again"}))
    async with httpx.AsyncClient(transport=redirect) as client:
        with pytest.raises(ToolError) as error:
            await HttpPageProvider(client, robots=Robots(), max_redirects=1).open("https://example.test")
        assert error.value.code == "redirect_limit"
        with pytest.raises(ToolError) as denied:
            await HttpPageProvider(client, robots=Robots(False)).open("https://example.test")
        assert denied.value.code == "robots_denied"
    unsupported = httpx.MockTransport(lambda request: httpx.Response(
        200, headers={"content-type": "application/octet-stream"}, content=b"x"))
    async with httpx.AsyncClient(transport=unsupported) as client:
        with pytest.raises(ToolError) as error:
            await HttpPageProvider(client, robots=Robots()).open("https://example.test")
        assert error.value.code == "unsupported_format"

@pytest.mark.asyncio
async def test_provider_timeout_is_structured():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ToolError) as error:
            await HttpPageProvider(client, robots=Robots()).open("https://example.test")
        assert error.value.code == "timeout"
