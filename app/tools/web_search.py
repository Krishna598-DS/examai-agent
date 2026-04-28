# app/tools/web_search.py
import httpx
from typing import Optional
from langchain.tools import tool
from app.config import settings
from app.logger import get_logger
from app.exceptions import SearchError

logger = get_logger(__name__)


async def search_serper(query: str, num_results: int = 5) -> dict:
    """
    Call the Serper API to get Google search results.

    Why Serper? It gives structured JSON results instead of raw HTML.
    We get title, snippet, and URL for each result — ready to use.

    Args:
        query: The search query string
        num_results: How many results to return (max 10 for free tier)

    Returns:
        Dictionary with organic search results
    """
    if not settings.serper_api_key:
        raise SearchError("SERPER_API_KEY is not set in environment")

    headers = {
        "X-API-KEY": settings.serper_api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": num_results,
        # gl = geographic location, hl = language
        # We set India + English for JEE/UPSC context
        "gl": "in",
        "hl": "en"
    }

    logger.info("search_started", query=query, num_results=num_results)

    # httpx.AsyncClient is the async HTTP client
    # We use it as a context manager (async with) so it automatically
    # closes the connection when done — prevents connection leaks
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                "https://google.serper.dev/search",
                headers=headers,
                json=payload
            )
            # Raise an exception if status code is 4xx or 5xx
            response.raise_for_status()
            results = response.json()

            logger.info(
                "search_completed",
                query=query,
                results_count=len(results.get("organic", []))
            )
            return results

        except httpx.TimeoutException:
            logger.error("search_timeout", query=query)
            raise SearchError(
                f"Search timed out for query: {query}",
                details={"query": query}
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "search_http_error",
                query=query,
                status_code=e.response.status_code
            )
            raise SearchError(
                f"Search API returned error: {e.response.status_code}",
                details={"query": query, "status_code": e.response.status_code}
            )


async def scrape_page(url: str) -> Optional[str]:
    """
    Fetch a web page and extract clean text from it.

    Why scrape? Search results give us snippets (2-3 sentences).
    For detailed answers we need the full page content.

    Args:
        url: The URL to scrape

    Returns:
        Clean text content of the page, or None if scraping fails
    """
    # Import here to avoid circular imports
    from bs4 import BeautifulSoup

    logger.info("scraping_page", url=url)

    async with httpx.AsyncClient(
        timeout=15.0,
        # Some sites block requests without a User-Agent header
        # We set a browser-like User-Agent to avoid being blocked
        headers={"User-Agent": "Mozilla/5.0 (compatible; ExamAI/1.0)"},
        # Follow redirects automatically (some URLs redirect to the real page)
        follow_redirects=True
    ) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()

            # BeautifulSoup parses the HTML
            # "lxml" is the parser — faster than Python's built-in html.parser
            soup = BeautifulSoup(response.text, "lxml")

            # Remove tags that contain no useful text
            # script = JavaScript code, style = CSS, nav = navigation menus
            # header/footer usually contain site chrome, not content
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()  # Remove the tag and its contents entirely

            # Extract text, separating elements with a space
            text = soup.get_text(separator=" ", strip=True)

            # Collapse multiple whitespace characters into single spaces
            import re
            text = re.sub(r'\s+', ' ', text).strip()

            # Limit to first 3000 characters
            # Why? LLMs have context limits. 3000 chars ≈ 750 tokens.
            # We'll get multiple sources so we don't need all of any one page.
            text = text[:3000]

            logger.info("scraping_completed", url=url, chars=len(text))
            return text

        except Exception as e:
            # Scraping fails often — paywalls, bot detection, timeouts
            # We log it but don't crash — we'll just use the snippet instead
            logger.warning("scraping_failed", url=url, error=str(e))
            return None


def format_search_results(results: dict, include_snippets: bool = True) -> str:
    """
    Convert raw Serper JSON into clean text the LLM can read.

    The LLM doesn't receive raw JSON — it receives formatted text
    that's easy to parse in natural language.
    """
    organic = results.get("organic", [])

    if not organic:
        return "No search results found."

    formatted = []
    for i, result in enumerate(organic, 1):
        title = result.get("title", "No title")
        url = result.get("link", "")
        snippet = result.get("snippet", "No description available")

        entry = f"[{i}] {title}\nURL: {url}"
        if include_snippets:
            entry += f"\nSummary: {snippet}"
        formatted.append(entry)

    return "\n\n".join(formatted)
