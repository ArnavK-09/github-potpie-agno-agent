#############
## IMPORTS ##
############# 
import asyncio
import random
from agno.agent import Agent
from agno.storage.sqlite import SqliteStorage
from agno.models.groq import Groq
from agno.tools import tool
from typing import Dict, Any
import requests
import logging
import time
from typing import List, Optional

############
## CONSTS ##
############ 
GROQ_API_KEY = "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"
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
            time.sleep(poll_interval)

    def create_conversation(self, project_ids: List[str], agent_ids: List[str]) -> Dict[str, Any]:
        """Create a new conversation."""
        endpoint = "/conversations"
        payload = {"project_ids": project_ids, "agent_ids": agent_ids}
        return self._make_request("POST", endpoint, json_data=payload)

    def send_message(self, conversation_id: str, content: str, agent_id: str, node_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send a message within a conversation."""
        endpoint = f"/conversations/{conversation_id}/message"
        payload = {
            "content": content,
            "agent_id": agent_id,
            "node_ids": node_ids if node_ids is not None else []
        }
        return self._make_request("POST", endpoint, json_data=payload)



#################
## AGENT TOOLS ##
#################

@tool(show_result=True)
def get_repository_trends(repo_url: str) -> Dict[str, Any]:
    """Get trending metrics for a GitHub repository over time."""
    # Mock trend data
    return {
        'star_growth': f"{random.randint(1, 100)}% increase in last month",
        'fork_growth': f"{random.randint(1, 50)}% increase in last month",
    'contributor_growth': f"{random.randint(1, 30)} new contributors in last month",
            'commit_frequency_trend': random.choice(['Increasing', 'Stable', 'Decreasing'])
    }


@tool(show_result=True)
def analyze_repository(repo_url: str) -> Dict[str, Any]:
    """Analyze a GitHub repository and return various metrics."""
    # Mock data generation
    analysis = {
        'stars': random.randint(0, 10000),
        'forks': random.randint(0, 2000),
        'commit_frequency': random.choice(['High', 'Medium', 'Low']),
        'issue_response_time': f"{random.randint(1, 72)} hours",
        'documentation_quality': random.randint(1, 10),
        'overall_score': random.randint(1, 100)
    }

    # Add mock insights
    analysis['insights'] = {
        'code_quality': random.choice(['Excellent', 'Good', 'Fair', 'Needs Improvement']),
        'community_engagement': random.choice(['Very Active', 'Active', 'Moderate', 'Low']),
        'maintenance_status': random.choice(['Well Maintained', 'Regularly Updated', 'Needs Attention'])
    }

    return str(analysis)



################
## AGENT INIT ##
################
github_agent = Agent(
    name="GitHub QnA Agent",
    model=Groq(api_key=GROQ_API_KEY),
    tools=[analyze_repository],
    instructions=[
        "You are a GitHub QnA agent. User can ask questions about GitHub repositories and you will answer them.",
        "Use tools given to you to get the answer, do not try to answer them yourself.",
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
    message = input("Enter your message: ") 
    print(f"--- Sending message to agent: '{message}' ---")
    # Run the agent and stream the response
    await github_agent.aprint_response(message, stream=True, show_tool_calls=True)

    print("\n--- Agent finished ---")


###############
## RUN AGENT ##
###############
if __name__ == "__main__":
    asyncio.run(main())