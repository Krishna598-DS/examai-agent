# app/tools/web_search.py
import httpx
import re
from typing import Optional
from app.config import settings
from app.logger import get_logger
from app.exceptions import SearchError
from app.tools.retry import retryable
from app.tools.rate_limiter import serper_limiter

logger = get_logger(__name__)


@retryable(
    max_retries=3,
    base_delay=1.0,
    # Only retry on these exceptions — don't retry on bad API keys
    retryable_exceptions=(httpx.TimeoutException, httpx.NetworkError)
)
async def search_serper(query: str, num_results: int = 5) -> dict:
    """
    Call the Serper API with retry logic and rate limiting.
    """
    if not settings.serper_api_key:
        raise SearchError("SERPER_API_KEY is not set in environment")

    # Acquire rate limit slot before making the call
    # This blocks if we've made too many calls recently
    async with serper_limiter:
        headers = {
            "X-API-KEY": settings.serper_api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": num_results,
            "gl": "in",
            "hl": "en"
        }

        logger.info("search_started", query=query, num_results=num_results)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                results = response.json()

                logger.info(
                    "search_completed",
                    query=query,
                    results_count=len(results.get("organic", []))
                )
                return results

            except httpx.HTTPStatusError as e:
                # 429 = rate limited by Serper itself
                if e.response.status_code == 429:
                    logger.warning("serper_rate_limited", query=query)
                    raise httpx.NetworkError("Rate limited by Serper")

                # 401/403 = bad API key — don't retry
                if e.response.status_code in (401, 403):
                    raise SearchError(
                        "Invalid Serper API key",
                        details={"status_code": e.response.status_code}
                    )

                raise SearchError(
                    f"Search API error: {e.response.status_code}",
                    details={"query": query}
                )


async def scrape_page(url: str, max_chars: int = 3000) -> Optional[str]:
    """
    Fetch a web page and extract clean readable text.

    Falls back gracefully — if scraping fails for any reason,
    returns None so the agent can use the snippet instead.
    Graceful degradation > crashing.
    """
    logger.info("scraping_started", url=url)

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
        follow_redirects=True
    ) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()

            # Only process HTML pages — skip PDFs, images, etc.
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                logger.info("scraping_skipped_non_html",
                           url=url, content_type=content_type)
                return None

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")

            # Remove noise tags
            for tag in soup(["script", "style", "nav", "header",
                             "footer", "aside", "advertisement"]):
                tag.decompose()

            # Try to find the main content area first
            # Many sites use <main>, <article>, or role="main"
            # This gives us the actual content, not sidebar/nav text
            main_content = (
                soup.find("main") or
                soup.find("article") or
                soup.find(attrs={"role": "main"}) or
                soup.find("div", class_=re.compile(r"content|article|post",
                                                    re.I))
            )

            # Use main content if found, otherwise use full body
            target = main_content if main_content else soup

            text = target.get_text(separator=" ", strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            text = text[:max_chars]

            logger.info(
                "scraping_completed",
                url=url,
                chars=len(text),
                used_main_content=main_content is not None
            )
            return text

        except httpx.TimeoutException:
            logger.warning("scraping_timeout", url=url)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("scraping_http_error",
                          url=url, status=e.response.status_code)
            return None
        except Exception as e:
            logger.warning("scraping_failed", url=url, error=str(e))
            return None


async def search_and_scrape(
    query: str,
    num_results: int = 3,
    scrape_top_n: int = 2
) -> str:
    """
    Search + scrape pipeline.

    1. Search for query → get snippets + URLs
    2. Scrape top N pages → get full content
    3. Combine snippets (for pages that failed) with full content

    This gives the agent much richer information than snippets alone.
    scrape_top_n=2 means we scrape the top 2 results fully,
    and use snippets for the rest. Good balance of depth vs speed.
    """
    import asyncio

    results = await search_serper(query, num_results)
    organic = results.get("organic", [])

    if not organic:
        return "No search results found."

    # Scrape top N pages concurrently
    urls_to_scrape = [r.get("link", "") for r in organic[:scrape_top_n]]
    scraped_contents = await asyncio.gather(
        *[scrape_page(url) for url in urls_to_scrape],
        return_exceptions=True  # Don't crash if one scrape fails
    )

    # Build the final formatted output
    formatted = []
    for i, result in enumerate(organic):
        title = result.get("title", "No title")
        url = result.get("link", "")
        snippet = result.get("snippet", "")

        entry = f"[{i+1}] {title}\nURL: {url}\n"

        # Use full scraped content if available, otherwise snippet
        if i < scrape_top_n:
            scraped = scraped_contents[i]
            if isinstance(scraped, str) and scraped:
                entry += f"Content: {scraped}"
                logger.info("using_scraped_content", url=url)
            else:
                entry += f"Snippet: {snippet}"
                logger.info("using_snippet_fallback", url=url)
        else:
            entry += f"Snippet: {snippet}"

        formatted.append(entry)

    return "\n\n---\n\n".join(formatted)


def format_search_results(results: dict) -> str:
    """Format raw Serper results as readable text."""
    organic = results.get("organic", [])
    if not organic:
        return "No search results found."

    formatted = []
    for i, result in enumerate(organic, 1):
        title = result.get("title", "No title")
        url = result.get("link", "")
        snippet = result.get("snippet", "No description available")
        formatted.append(f"[{i}] {title}\nURL: {url}\nSummary: {snippet}")

    return "\n\n".join(formatted)
