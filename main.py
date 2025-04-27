import asyncio
import os
from textwrap import dedent

from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
from agno.tools import tool
import random
from mcp import StdioServerParameters
# Load environment variables from .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

from agno.tools.mcp import MCPTools



@tool(show_result=True, stop_after_tool_call=True)
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    # In a real implementation, this would call a weather API
    weather_conditions = ["sunny", "cloudy", "rainy", "snowy", "windy"]
    random_weather = random.choice(weather_conditions)

    return f"The weather in {city} is {random_weather}."



async def main():
    """Creates a basic agent using the Groq model and runs it."""
    # Ensure the Groq API key is set in the environment
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY environment variable not set.")
        print("Please create a .env file in the 'wow' directory with GROQ_API_KEY=your_api_key")
        return

    # Define the message to send to the agent
    message = input("Enter your message: ") 

    # Initialize the Groq model
    # You might need to specify the model name, e.g., model="llama3-8b-8192"
    # Check Groq documentation for available models
    model = Groq(api_key=GROQ_API_KEY)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        env={
            "MEMORY_FILE_PATH": "./memory.json"
        }
    )
    memory_tool = MCPTools(server_params=server_params)
    print(memory_tool)
    # Create the agent instance
    agent = Agent(
        model=model,
        reasoning=False,
        tools=[memory_tool],
        show_tool_calls=True,
        instructions="""Follow these steps for each interaction:

1. User Identification:
   - You should assume that you are interacting with default_user
   - If you have not identified default_user, proactively try to do so.

2. Memory Retrieval:
   - Always begin your chat by saying only "Remembering..." and retrieve all relevant information from your knowledge graph
   - Always refer to your knowledge graph as your "memory"

3. Memory
   - While conversing with the user, be attentive to any new information that falls into these categories:
     a) Basic Identity (age, gender, location, job title, education level, etc.)
     b) Behaviors (interests, habits, etc.)
     c) Preferences (communication style, preferred language, etc.)
     d) Goals (goals, targets, aspirations, etc.)
     e) Relationships (personal and professional relationships up to 3 degrees of separation)

4. Memory Update:
   - If any new information was gathered during the interaction, update your memory as follows:
     a) Create entities for recurring organizations, people, and significant events
     b) Connect them to the current entities using relations
     b) Store facts about them as observations"""
    )

    print(f"--- Sending message to agent: '{message}' ---")
    print(agent.tools)
    # Run the agent and stream the response
    await agent.aprint_response(message, stream=True)

    print("\n--- Agent finished ---")

if __name__ == "__main__":
    asyncio.run(main())
    

