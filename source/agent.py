#############
## IMPORTS ##
#############
import asyncio
import logging
import os
import random
import time
from typing import Any, Dict
from typing import List, Optional
from agno.agent import Agent
from agno.models.groq import Groq
from agno.storage.sqlite import SqliteStorage
from agno.tools import tool
from dotenv import load_dotenv
import requests

load_dotenv() # Load environment variables from .env file

############
## CONSTS ##
############
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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") # Use env var or default
POTPIE_API_KEY = os.getenv("POTPIE_API_KEY", "sk-23a7f4f61b60594953c6230fc22bd782231ced4ceeed4f23272d29b48e1ec655") # Get Potpie API key from environment
agent_storage: str = "tmp/agents.db"


###################
## POTPIE SYSTEM ##
###################
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [potpie-api] - %(levelname)s - %(message)s')

class Potpie:
    BASE_URL = "https://production-api.potpie.ai/api/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        logging.info(f"Making {method} request to {url} with data: {json_data}")
        try:
            response = requests.request(method, url, headers=self.headers, json=json_data)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            result = response.json()
            logging.info(f"Received response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            raise

    def parse_repository(self, repo_name: str, branch_name: str) -> Dict[str, Any]:
        """Initiate parsing for a given repository and branch."""
        endpoint = "/parse"
        payload = {"repo_name": repo_name, "branch_name": branch_name}
        return self._make_request("POST", endpoint, json_data=payload)

    def get_parsing_status(self, project_id: str, wait_for_ready: bool = True, timeout: int = 300, poll_interval: int = 10) -> Dict[str, Any]:
        """Get the parsing status for a project, optionally waiting until it's ready."""
        endpoint = f"/parsing-status/{project_id}"
        start_time = time.time()
        while True:
            status_data = self._make_request("GET", endpoint)
            if not wait_for_ready or status_data.get("status") == "ready":
                return status_data
            if time.time() - start_time > timeout:
                logging.error(f"Timeout waiting for project {project_id} to become ready.")
                raise TimeoutError(f"Project {project_id} did not become ready within {timeout} seconds.")
            logging.info(f"Project {project_id} status is {status_data.get('status')}. Waiting...")
            # Removed duplicate logging line here
            time.sleep(poll_interval)

    def create_conversation(self, project_ids: List[str], agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new conversation."""
        endpoint = "/conversations"
        payload = {"project_ids": project_ids}
        if agent_ids:
            payload["agent_ids"] = agent_ids
        return self._make_request("POST", endpoint, json_data=payload)

    def send_message(self, conversation_id: str, content: str, agent_id: Optional[str] = None, node_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send a message within a conversation."""
        endpoint = f"/conversations/{conversation_id}/message"
        payload = {
            "content": content,
            "agent_id": agent_id, # Potpie API might handle missing agent_id gracefully or have defaults
            "node_ids": node_ids if node_ids is not None else []
        }
        return self._make_request("POST", endpoint, json_data=payload)


# Initialize Potpie client if API key is available
potpie_client = None
if POTPIE_API_KEY:
    potpie_client = Potpie(api_key=POTPIE_API_KEY)
else:
    logging.warning("Potpie API key not found. Potpie tools will be unavailable.")


#################
## AGENT TOOLS ##
#################

# --- Potpie Tools ---

@tool(show_result=True)
def start_repo_parsing(repo_name: str, branch_name: str = "main") -> Dict[str, Any]:
    """
    Initiates the parsing process for a given repository and branch using Potpie.
    Returns the initial parsing status, including the project_id needed for follow-up actions.
    Example repo_name: 'owner/repo'
    """
    if not potpie_client:
        return {"error": "Potpie client not initialized. Check POTPIE_API_KEY."}
    try:
        logging.info(f"Starting parsing for {repo_name} on branch {branch_name}")
        # Run synchronous network I/O in a separate thread
        result = asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(potpie_client.parse_repository, repo_name=repo_name, branch_name=branch_name),
            asyncio.get_running_loop()
        ).result()
        logging.info(f"Parsing initiated: {result}")
        return result # Return the initial response which contains project_id
    except Exception as e:
        logging.error(f"Error starting repo parsing for {repo_name}: {e}")
        return {"error": f"Failed to start parsing: {str(e)}"}

@tool(show_result=True)
def check_repo_parsing_status(project_id: str) -> Dict[str, Any]:
    """
    Checks the parsing status of a repository using its Potpie project_id.
    """
    if not potpie_client:
        return {"error": "Potpie client not initialized. Check POTPIE_API_KEY."}
    try:
        logging.info(f"Checking parsing status for project_id: {project_id}")
        # Run synchronous network I/O in a separate thread
        status = asyncio.run_coroutine_threadsafe(
             asyncio.to_thread(potpie_client.get_parsing_status, project_id, wait_for_ready=False),
             asyncio.get_running_loop()
        ).result()
        logging.info(f"Parsing status for {project_id}: {status}")
        return status
    except Exception as e:
        logging.error(f"Error checking parsing status for {project_id}: {e}")
        return {"error": f"Failed to get parsing status: {str(e)}"}


@tool(show_result=True)
async def ask_parsed_repo(project_id: str, query: str) -> Dict[str, Any]:
    """
    Asks a question about a repository that has already been parsed by Potpie,
    identified by its project_id. Waits for parsing to complete if not already ready.
    """
    if not potpie_client:
        return {"error": "Potpie client not initialized. Check POTPIE_API_KEY."}
    try:
        logging.info(f"Querying project_id: {project_id} with query: '{query}'")
        # Ensure the project is ready before querying (run sync I/O in thread)
        parsing_status = await asyncio.to_thread(potpie_client.get_parsing_status, project_id, wait_for_ready=True, timeout=600) # Wait up to 10 mins
        if parsing_status.get("status") != "ready":
            return {"error": f"Project {project_id} is not ready for querying. Status: {parsing_status.get('status')}"}

        # Create a conversation for this query (run sync I/O in thread)
        conversation_data = await asyncio.to_thread(potpie_client.create_conversation, project_ids=[project_id])
        conversation_id = conversation_data.get("conversation_id")
        if not conversation_id:
            return {"error": "Failed to create Potpie conversation."}

        logging.info(f"Created conversation {conversation_id} for project {project_id}")

        # Send the message/query (run sync I/O in thread)
        message_response = await asyncio.to_thread(potpie_client.send_message, conversation_id=conversation_id, content=query)
        logging.info(f"Received response for query on {project_id}: {message_response}")

        return message_response # Return the full response for now

    except TimeoutError as e:
        logging.error(f"Timeout waiting for project {project_id} to be ready: {e}")
        return {"error": f"Timeout waiting for repository parsing to complete: {str(e)}"}
    except Exception as e:
        logging.error(f"Error querying parsed repo {project_id}: {e}")
        return {"error": f"Failed to query repository: {str(e)}"}


# --- Potpie-based Analysis and Trends Tools ---

@tool(show_result=True)
async def analyze_repository(repo_name: str) -> Dict[str, Any]:
    """
    Analyze a GitHub repository using Potpie and return various metrics.
    Expects repo_name like 'owner/repo'. This tool handles parsing initiation and querying.
    """
    if not potpie_client:
        return {"error": "Potpie client not initialized. Check POTPIE_API_KEY."}

    try:
        # 1. Start parsing
        logging.info(f"analyze_repository: Starting parsing for {repo_name}")
        parse_result = await asyncio.to_thread(potpie_client.parse_repository, repo_name=repo_name, branch_name="main")
        project_id = parse_result.get("project_id")
        if not project_id:
            return {"error": f"Failed to get project_id when starting parsing for {repo_name}. Response: {parse_result}"}
        logging.info(f"analyze_repository: Parsing started for {repo_name}, project_id: {project_id}. Waiting for completion...")

        # 2. Ask Potpie for the analysis data (ask_parsed_repo handles waiting)
        analysis_query = (
            "Provide a detailed analysis of this repository including: "
            "current number of stars, current number of forks, typical commit frequency (e.g., High, Medium, Low), "
            "estimated average issue response time, assessment of documentation quality (e.g., score 1-10 or description), "
            "overall code quality assessment (e.g., Excellent, Good, Fair), community engagement level (e.g., Very Active, Active, Low), "
            "and maintenance status (e.g., Well Maintained, Needs Attention)."
        )
        logging.info(f"analyze_repository: Querying project {project_id} for analysis.")
        analysis_response = await ask_parsed_repo(project_id=project_id, query=analysis_query) # ask_parsed_repo now handles waiting
        logging.info(f"analyze_repository: Received analysis response for {project_id}: {analysis_response}")

        # 3. Format/Return the response
        if isinstance(analysis_response, dict) and "error" in analysis_response:
             return {"error": f"Potpie query failed for analysis: {analysis_response['error']}"}
        # Assuming the actual answer is nested within the response structure
        elif isinstance(analysis_response, dict) and "response" in analysis_response:
             return {"potpie_analysis_response": analysis_response["response"]}
        else:
             return {"potpie_analysis_raw": analysis_response} # Fallback

    except TimeoutError as e:
        logging.error(f"Timeout during analysis for {repo_name}: {e}")
        return {"error": f"Timeout waiting for repository parsing/analysis: {str(e)}"}
    except Exception as e:
        logging.error(f"Error during repository analysis for {repo_name}: {e}")
        return {"error": f"Failed to analyze repository: {str(e)}"}


@tool(show_result=True)
async def get_repository_trends(repo_name: str) -> Dict[str, Any]:
    """
    Get trending metrics for a GitHub repository using Potpie.
    Expects repo_name like 'owner/repo'. This tool handles parsing initiation and querying.
    """
    if not potpie_client:
        return {"error": "Potpie client not initialized. Check POTPIE_API_KEY."}

    try:
        # 1. Start parsing
        logging.info(f"get_repository_trends: Starting parsing for {repo_name}")
        parse_result = await asyncio.to_thread(potpie_client.parse_repository, repo_name=repo_name, branch_name="main")
        project_id = parse_result.get("project_id")
        if not project_id:
            return {"error": f"Failed to get project_id when starting parsing for {repo_name}. Response: {parse_result}"}
        logging.info(f"get_repository_trends: Parsing started for {repo_name}, project_id: {project_id}. Waiting for completion...")

        # 2. Ask Potpie for the trends data
        trends_query = (
            "Provide recent trending metrics for this repository including: "
            "star growth rate (e.g., percentage increase over the last month), "
            "fork growth rate (e.g., percentage increase over the last month), "
            "new contributor growth (e.g., number of new contributors in the last month), "
            "and the recent commit frequency trend (e.g., Increasing, Stable, Decreasing)."
        )
        logging.info(f"get_repository_trends: Querying project {project_id} for trends.")
        trends_response = await ask_parsed_repo(project_id=project_id, query=trends_query) # ask_parsed_repo handles waiting
        logging.info(f"get_repository_trends: Received trends response for {project_id}: {trends_response}")

        # 3. Format/Return the response
        if isinstance(trends_response, dict) and "error" in trends_response:
             return {"error": f"Potpie query failed for trends: {trends_response['error']}"}
        elif isinstance(trends_response, dict) and "response" in trends_response:
             # TODO: Implement robust parsing of Potpie's response text/structure here
             return {"potpie_trends_response": trends_response["response"]}
        else:
             return {"potpie_trends_raw": trends_response} # Fallback

    except TimeoutError as e:
        logging.error(f"Timeout during trend analysis for {repo_name}: {e}")
        return {"error": f"Timeout waiting for repository parsing/trends: {str(e)}"}
    except Exception as e:
        logging.error(f"Error during repository trend analysis for {repo_name}: {e}")
        return {"error": f"Failed to get repository trends: {str(e)}"}


################
## AGENT INIT ##
################

# Combine all tools
agent_tools = [
    start_repo_parsing,
    check_repo_parsing_status,
    ask_parsed_repo,
    analyze_repository, # Now uses Potpie
    get_repository_trends # Now uses Potpie
]

# Filter out tools if Potpie client isn't available
# Now all tools except potentially check_repo_parsing_status (if used standalone) depend on Potpie
if not potpie_client:
    # All primary tools depend on Potpie now
    potpie_dependent_tool_names = ['start_repo_parsing', 'check_repo_parsing_status', 'ask_parsed_repo', 'analyze_repository', 'get_repository_trends']
    original_tools = agent_tools[:] # Make a copy
    agent_tools = []
    # This loop could be simplified to just setting agent_tools = [] if all tools require potpie
    # for t in original_tools:
    #      if hasattr(t, 'func') and getattr(t.func, '__name__', None) in potpie_dependent_tool_names:
    #          continue
    #      agent_tools.append(t)
    print("Potpie tools disabled due to missing API key. Agent will have no functional tools.")


github_agent = Agent(
    name="GitHub QnA Agent",
    model=Groq(api_key=GROQ_API_KEY),
    tools=agent_tools,
    instructions=[
        "You are a specialized GitHub QnA agent.",
        "You have access to tools for analyzing repositories using Potpie.",
        "To answer questions about a specific repository's code or structure (e.g., 'What does function X do?', 'Summarize class Y', 'Find usages of Z'):",
        "1. Use 'start_repo_parsing' with the 'owner/repo' name. Get the 'project_id'.",
        "2. Inform the user parsing started.",
        "3. Use 'ask_parsed_repo' with the 'project_id' and the specific query. This tool waits for parsing to finish.",
        "To get a general analysis or metrics for a repository:",
        "1. Use the 'analyze_repository' tool with the 'owner/repo' name. This tool handles parsing and querying Potpie for analysis data.",
        "To get repository trends:",
        "1. Use the 'get_repository_trends' tool with the 'owner/repo' name. This tool handles parsing and querying Potpie for trend data.",
        "If the Potpie client is unavailable (due to missing API key), inform the user that parsing, code questions, analysis, and trends are not possible.",
        "Provide clear responses based *only* on the tool outputs.",
        "If a tool returns an error, report it clearly.",
    ],
    storage=SqliteStorage(table_name="github_agent", db_file=agent_storage),
    add_datetime_to_instructions=True,
    add_history_to_messages=True,
    num_history_responses=5,
    markdown=True,
)


################
## ENTRYPOINT ##
################
async def main():
    """Creates a basic agent using the Groq model and runs it."""
    # Check if essential Potpie tools are missing due to API key
    potpie_essentials_missing = False
    if not potpie_client:
        potpie_essentials_missing = True
        print("CRITICAL: POTPIE_API_KEY is not set in .env. Potpie-dependent tools (parsing, code QnA, analysis) are disabled.")

    message = input("Enter your message: ")
    print(f"--- Sending message to agent: '{message}' ---")
    # Run the agent and stream the response - Use aprint_response for async tool calls
    await github_agent.aprint_response(message, stream=True, show_tool_calls=True)

    print("\n--- Agent finished ---")


###############
## RUN AGENT ##
###############
if __name__ == "__main__":
    asyncio.run(main())
