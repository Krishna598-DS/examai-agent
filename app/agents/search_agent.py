# app/agents/search_agent.py
# app/agents/search_agent.py
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Optional
from app.tools.web_search import search_and_scrape, format_search_results
from app.config import settings
from app.logger import get_logger
from app.exceptions import AgentError, SearchError

logger = get_logger(__name__)


# Pydantic model for tool input validation
# LangChain uses this to validate what the agent passes to the tool
class SearchInput(BaseModel):
    query: str = Field(
        description="The search query to look up on Google. "
                    "Be specific and include relevant context like "
                    "'JEE Physics' or 'UPSC History' for better results."
    )
    num_results: int = Field(
        default=5,
        description="Number of search results to return (1-10)",
        ge=1,
        le=10
    )


async def search_tool_func(query: str, num_results: int = 5) -> str:
    """
    Search + scrape for richer content.
    Falls back to snippet-only if scraping fails.
    """
    try:
        # Use the richer search_and_scrape pipeline
        return await search_and_scrape(
            query,
            num_results=num_results,
            scrape_top_n=2
        )
    except SearchError as e:
        return f"Search failed: {e.message}"

# SYSTEM PROMPT — this is what shapes the agent's personality and behavior
# This is one of the most important parts of agent engineering.
# A well-crafted system prompt = reliable agent behavior.
# A vague system prompt = unpredictable, unreliable agent.
SEARCH_AGENT_PROMPT = PromptTemplate.from_template("""
You are an expert research assistant specializing in Indian competitive exams,
particularly JEE (Joint Entrance Examination) and UPSC (Union Public Service Commission).

Your job is to answer questions accurately by searching for relevant information.
Always search before answering — never rely on memory alone.

For JEE questions: focus on Physics, Chemistry, and Mathematics concepts.
For UPSC questions: focus on History, Polity, Geography, Economics, and Current Affairs.

Always cite your sources by mentioning the URL where you found information.
If search results are insufficient, search again with a different query.

You have access to the following tools:
{tools}

Use the following format EXACTLY:

Question: the input question you must answer
Thought: think about what you need to search for and why
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have enough information to answer the question
Final Answer: the complete answer with sources cited

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")


class SearchAgent:
    """
    Autonomous web search agent using the ReAct pattern.

    This agent:
    1. Receives a question
    2. Decides what to search for
    3. Reads search results
    4. Decides if more searching is needed
    5. Returns a sourced answer

    It's "autonomous" because steps 2-4 happen without human intervention.
    """

    def __init__(self):
        # Initialize the LLM
        # temperature=0 means deterministic — same question = same reasoning
        # For agents, you want low temperature for consistent tool use decisions
        # Higher temperature = more creative but less reliable tool calling
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Fast and cheap — good for search tasks
            temperature=0,
            api_key=settings.openai_api_key,
            # Timeout for each LLM call
            request_timeout=settings.agent_timeout_seconds,
        )

        # Define the tools the agent can use
        # StructuredTool validates inputs using the Pydantic schema
        self.tools = [
            StructuredTool.from_function(
                coroutine=search_tool_func,  # async function
                name="web_search",
                description=(
                    "Search Google for information about JEE or UPSC topics. "
                    "Use this to find explanations, examples, and facts. "
                    "Input should be a specific search query."
                ),
                args_schema=SearchInput,
            )
        ]

        # Create the ReAct agent
        # create_react_agent combines the LLM + tools + prompt
        # into the Thought/Action/Observation loop
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=SEARCH_AGENT_PROMPT,
        )

        # AgentExecutor runs the agent loop
        # max_iterations: stop after this many Thought/Action cycles
        # This prevents infinite loops if the agent gets confused
        # handle_parsing_errors: if the LLM outputs malformed ReAct format,
        # try to recover instead of crashing
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=5,
            handle_parsing_errors=True,
            verbose=settings.is_development,  # Print ReAct loop in development
        )

        logger.info("search_agent_initialized", model="gpt-4o-mini")

    async def run(self, question: str) -> dict:
        """
        Run the search agent on a question.

        Args:
            question: The JEE/UPSC question to research

        Returns:
            Dictionary with answer and metadata
        """
        import time
        start = time.time()

        logger.info("search_agent_started", question=question[:100])

        try:
            result = await self.executor.ainvoke(
                {"input": question}
            )

            duration = round(time.time() - start, 2)

            logger.info(
                "search_agent_completed",
                question=question[:100],
                duration_seconds=duration,
            )

            return {
                "answer": result["output"],
                "agent": "search",
                "duration_seconds": duration,
                "question": question,
            }

        except Exception as e:
            logger.error(
                "search_agent_failed",
                question=question[:100],
                error=str(e)
            )
            raise AgentError(
                message=f"Search agent failed: {str(e)}",
                details={"question": question}
            )


# Module-level singleton instance
# Created once when the module is first imported
# Reused for all subsequent requests — avoids reinitializing the LLM client
search_agent = SearchAgent()
