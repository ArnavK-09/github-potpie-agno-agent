#############
## IMPORTS ##
#############
from agent import github_agent
from agno.playground import Playground, serve_playground_app

#################
## APPLICATION ##
#################
app = Playground(agents=[github_agent]).get_app()

################
## PLAYGROUND ##
################
if __name__ == "__main__":
    server = serve_playground_app("playground:app", reload=True)
    print(server)