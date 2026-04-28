# app/agents/search_agent.py
import time
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from app.tools.web_search import search_and_scrape
from app.config import settings
from app.logger import get_logger
from app.exceptions import AgentError, SearchError

logger = get_logger(__name__)


@tool
async def web_search(query: str, num_results: int = 5) -> str:
    """
    Search Google for information about JEE or UPSC topics.
    Use this to find explanations, examples, and facts.
    Input should be a specific search query including subject context.
    """
    try:
        return await search_and_scrape(
            query, num_results=num_results, scrape_top_n=2
        )
    except SearchError as e:
        return f"Search failed: {e.message}"


SYSTEM_PROMPT = """You are an expert research assistant for Indian competitive 
exams (JEE and UPSC). Always search before answering. Cite sources with URLs.
For JEE: focus on Physics, Chemistry, Math concepts and formulas.
For UPSC: focus on History, Polity, Geography, Economics, Current Affairs."""


class SearchAgent:
    """
    Search agent using LangGraph's built-in create_react_agent.
    This handles the message ordering and tool call loop correctly.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )

        self.tools = [web_search]

        # create_react_agent from langgraph.prebuilt handles everything:
        # - binding tools to the LLM
        # - the tool call loop
        # - message state management
        # - correct message ordering (no more tool role errors)
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SYSTEM_PROMPT,
        )

        logger.info("search_agent_initialized", framework="langgraph_prebuilt")

    async def run(self, question: str) -> dict:
        """Run the agent on a question."""
        start = time.time()
        logger.info("search_agent_started", question=question[:100])

        try:
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]}
            )

            # Last message in the list is the final answer
            last_message = result["messages"][-1]
            answer = last_message.content

            duration = round(time.time() - start, 2)
            logger.info("search_agent_completed", duration_seconds=duration)

            return {
                "answer": answer,
                "agent": "search",
                "duration_seconds": duration,
                "question": question,
            }

        except Exception as e:
            logger.error("search_agent_failed", error=str(e))
            raise AgentError(
                f"Search agent failed: {str(e)}",
                details={"question": question}
            )


# Singleton
search_agent = SearchAgent()
