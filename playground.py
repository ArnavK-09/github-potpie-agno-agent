from agno.agent import Agent
from agno.playground import Playground, serve_playground_app
from agno.storage.sqlite import SqliteStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.models.groq import Groq
from github_tools import GitHubTools

GROQ_API_KEY = "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"

agent_storage: str = "tmp/agents.db"


github_agent = Agent(
    name="GitHub QnA Agent",
    model=Groq(api_key=GROQ_API_KEY),
    tools=[GitHubTools()],
    instructions=[
        "Analyze GitHub repositories and provide detailed ratings",
        "Present metrics in a clear, tabulated format",
        "Include both quantitative and qualitative insights",
        "Provide trend analysis when available"
    ],
    storage=SqliteStorage(table_name="github_agent", db_file=agent_storage),
    add_datetime_to_instructions=True,
    add_history_to_messages=True,
    num_history_responses=5,
    markdown=True,
)

app = Playground(agents=[github_agent]).get_app()

if __name__ == "__main__":
    server = serve_playground_app("playground:app", reload=True)
    print(server)