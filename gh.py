import asyncio
import os
from textwrap import dedent

from agno.agent import Agent
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters
from agno.models.groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
model = Groq(api_key=GROQ_API_KEY)
async def run_agent(message: str) -> None:
    """Run the GitHub agent with the given message."""

    # Initialize the MCP server
    server_params = StdioServerParameters(
        command="uvx",
        args=["-y", "mcp-server-time"],
    )

    # Create a client session to connect to the MCP server
    async with MCPTools(server_params=server_params) as mcp_tools:
        agent = Agent(model=model,
            tools=[mcp_tools],
            instructions=dedent("""\
                You are a GitHub assistant. Help users explore repositories and their activity.

                - Use headings to organize your responses
                - Be concise and focus on relevant information\
            """),
            markdown=True,
            show_tool_calls=True
        )

        # Run the agent
        await agent.aprint_response(message, stream=True)


# Example usage
if __name__ == "__main__":
    # Pull request example
    asyncio.run(
        run_agent(
            "hi"
        )
    )

