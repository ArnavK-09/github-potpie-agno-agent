#############
## IMPORTS ##
#############
import asyncio
import logging
import os
import time
from typing import Any, Dict
from typing import List, Optional
from agno.agent import Agent
from agno.models.groq import Groq
from agno.storage.sqlite import SqliteStorage
from agno.tools import tool
from dotenv import load_dotenv
import requests

#########
## ENV ##
#########
load_dotenv()

############
## CONSTS ##
############
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
POTPIE_API_KEY = os.getenv("POTPIE_API_KEY")
agent_storage: str = ".temp/agents.db"


###################
## POTPIE SYSTEM ##
###################
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
            response.raise_for_status()
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
            "agent_id": agent_id,
            "node_ids": node_ids if node_ids is not None else []
        }
        return self._make_request("POST", endpoint, json_data=payload)


# Initialize Potpie client
potpie_client = Potpie(api_key=POTPIE_API_KEY)


#################
## AGENT TOOLS ##
#################

@tool(show_result=True)
async def start_repo_parsing(repo_name: str, branch_name: str = "main") -> str:
    """
    Initiates the parsing process for a given repository and branch using Potpie.
    Returns the initial parsing status, including the project_id needed for follow-up actions.
    Example repo_name: 'owner/repo'
    """
    try:
        if not repo_name or '/' not in repo_name:
            return "Invalid repository name format. Expected format: 'owner/repo'"
            
        logging.info(f"Starting parsing for {repo_name} on branch {branch_name}")
        result = await asyncio.to_thread(potpie_client.parse_repository, repo_name=repo_name, branch_name=branch_name)
        
        if isinstance(result, dict) and 'project_id' in result:
            project_id = result['project_id']
            logging.info(f"Parsing initiated successfully: {result}")
            return f"Successfully started parsing repository {repo_name}\nProject ID: {project_id}\nStatus: Parsing initiated"
        else:
            logging.error(f"Invalid response format from Potpie API: {result}")
            return f"Failed to parse repository: Invalid API response format"
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error during repo parsing for {repo_name}: {e}")
        return f"Failed to parse repository: Network error - {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error during repo parsing for {repo_name}: {e}")
        return f"Failed to parse repository: {str(e)}"

@tool(show_result=True)
async def check_repo_parsing_status(project_id: str) -> str:
    """
    Checks the parsing status of a repository using its Potpie project_id.
    """
    try:
        if not project_id:
            return "Invalid project_id: Project ID cannot be empty"
            
        logging.info(f"Checking parsing status for project_id: {project_id}")
        status = await asyncio.to_thread(potpie_client.get_parsing_status, project_id, wait_for_ready=False)
        
        if isinstance(status, dict):
            status_value = status.get('status')
            if status_value:
                logging.info(f"Parsing status for {project_id}: {status}")
                return f"Current parsing status: {status_value}"
            else:
                logging.error(f"Invalid status response format: {status}")
                return "Failed to get parsing status: Invalid response format"
        else:
            logging.error(f"Invalid response type from Potpie API: {type(status)}")
            return "Failed to get parsing status: Invalid API response type"
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error checking parsing status for {project_id}: {e}")
        return f"Failed to get parsing status: Network error - {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error checking parsing status for {project_id}: {e}")
        return f"Failed to get parsing status: {str(e)}"


@tool(show_result=True)
async def ask_parsed_repo(project_id: str, query: str) -> str:
    """
    Asks a question about a repository that has already been parsed by Potpie,
    identified by its project_id. Waits for parsing to complete if not already ready.
    """
    try:
        logging.info(f"Querying project_id: {project_id} with query: '{query}'")
        parsing_status = await asyncio.to_thread(potpie_client.get_parsing_status, project_id, wait_for_ready=True, timeout=600)
        if parsing_status.get("status") != "ready":
            return f"Project {project_id} is not ready for querying. Status: {parsing_status.get('status')}"

        conversation_data = await asyncio.to_thread(potpie_client.create_conversation, project_ids=[project_id])
        conversation_id = conversation_data.get("conversation_id")
        if not conversation_id:
            return "Failed to create Potpie conversation."

        logging.info(f"Created conversation {conversation_id} for project {project_id}")

        message_response = await asyncio.to_thread(potpie_client.send_message, conversation_id=conversation_id, content=query)
        logging.info(f"Received response for query on {project_id}: {message_response}")

        return str(message_response)

    except TimeoutError as e:
        logging.error(f"Timeout waiting for project {project_id} to be ready: {e}")
        return f"Timeout waiting for repository parsing to complete: {str(e)}"
    except Exception as e:
        logging.error(f"Error querying parsed repo {project_id}: {e}")
        return f"Failed to query repository: {str(e)}"


@tool(show_result=True)
async def analyze_repository(repo_name: str) -> str:
    """
    Analyze a GitHub repository using Potpie and return various metrics.
    Expects repo_name like 'owner/repo'. This tool handles parsing initiation and querying.
    """
    try:
        logging.info(f"analyze_repository: Starting parsing for {repo_name}")
        parse_result = await asyncio.to_thread(potpie_client.parse_repository, repo_name=repo_name, branch_name="main")
        project_id = parse_result.get("project_id")
        if not project_id:
            return f"Failed to get project_id when starting parsing for {repo_name}. Response: {parse_result}"
        logging.info(f"analyze_repository: Parsing started for {repo_name}, project_id: {project_id}. Waiting for completion...")

        analysis_query = (
            "Provide a detailed analysis of this repository including: "
            "current number of stars, current number of forks, typical commit frequency (e.g., High, Medium, Low), "
            "estimated average issue response time, assessment of documentation quality (e.g., score 1-10 or description), "
            "overall code quality assessment (e.g., Excellent, Good, Fair), community engagement level (e.g., Very Active, Active, Low), "
            "and maintenance status (e.g., Well Maintained, Needs Attention)."
        )
        logging.info(f"analyze_repository: Querying project {project_id} for analysis.")
        analysis_response = await ask_parsed_repo(project_id=project_id, query=analysis_query)
        logging.info(f"analyze_repository: Received analysis response for {project_id}: {analysis_response}")

        if analysis_response.startswith("Failed"):
            return analysis_response
        else:
            return f"Analysis of repository {repo_name}: {analysis_response}"

    except TimeoutError as e:
        logging.error(f"Timeout during analysis for {repo_name}: {e}")
        return f"Timeout waiting for repository parsing/analysis: {str(e)}"
    except Exception as e:
        logging.error(f"Error during repository analysis for {repo_name}: {e}")
        return f"Failed to analyze repository: {str(e)}"


@tool(show_result=True)
async def get_repository_trends(repo_name: str) -> str:
    """
    Get trending metrics for a GitHub repository using Potpie.
    Expects repo_name like 'owner/repo'. This tool handles parsing initiation and querying.
    """
    try:
        logging.info(f"get_repository_trends: Starting parsing for {repo_name}")
        parse_result = await asyncio.to_thread(potpie_client.parse_repository, repo_name=repo_name, branch_name="main")
        project_id = parse_result.get("project_id")
        if not project_id:
            return f"Failed to get project_id when starting parsing for {repo_name}. Response: {parse_result}"
        logging.info(f"get_repository_trends: Parsing started for {repo_name}, project_id: {project_id}. Waiting for completion...")

        trends_query = (
            "Provide recent trending metrics for this repository including: "
            "star growth rate (e.g., percentage increase over the last month), "
            "fork growth rate (e.g., percentage increase over the last month), "
            "new contributor growth (e.g., number of new contributors in the last month), "
            "and the recent commit frequency trend (e.g., Increasing, Stable, Decreasing)."
        )
        logging.info(f"get_repository_trends: Querying project {project_id} for trends.")
        trends_response = await ask_parsed_repo(project_id=project_id, query=trends_query)
        logging.info(f"get_repository_trends: Received trends response for {project_id}: {trends_response}")

        if isinstance(trends_response, dict) and "error" in trends_response:
             return f"Potpie query failed for trends: {trends_response['error']}"
        elif isinstance(trends_response, dict) and "response" in trends_response:
             return f"Potpie trends response for {repo_name}: {trends_response['response']}"
        else:
             return f"Potpie trends raw response for {repo_name}: {trends_response}"

    except TimeoutError as e:
        logging.error(f"Timeout during trend analysis for {repo_name}: {e}")
        return f"Timeout waiting for repository parsing/trends: {str(e)}"
    except Exception as e:
        logging.error(f"Error during repository trend analysis for {repo_name}: {e}")
        return f"Failed to get repository trends: {str(e)}"


################
## AGENT INIT ##
################
agent_tools = [
    start_repo_parsing,
    check_repo_parsing_status,
    ask_parsed_repo,
    analyze_repository,
    get_repository_trends
]

if not GROQ_API_KEY or not POTPIE_API_KEY:
    print("CRITICAL: Either GROQ_API_KEY or POTPIE_API_KEY is not set in .env. Potpie-dependent tools are disabled.")
    agent_tools = []

github_agent = Agent(
    name="GitHub QnA Agent",
    model=Groq(api_key=GROQ_API_KEY, max_retries=3),
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
    if not GROQ_API_KEY or not POTPIE_API_KEY:
        print("CRITICAL: Either GROQ_API_KEY or POTPIE_API_KEY is not set. Potpie-dependent tools are disabled.")
        return

    message = input("Enter your message: ")
    print(f"--- Sending message to agent: '{message}' ---")
    await github_agent.aprint_response(message, stream=True, show_tool_calls=True)

    print("\n--- Agent finished ---")


###############
## RUN AGENT ##
###############
if __name__ == "__main__":
    asyncio.run(main())
