import ollama
import time
import logging
log = logging.getLogger("applogger")

class LLMOllama:
  def __init__(self, database, model = "llama3"):
    self.database = database
    self.model = model

  def extend_api_description(self,query_string,path,operation,parameters):
    """
    Extend the description for each API REST Call operation

    Args:
        query_string (str): details of the REST API call
        path (str): REST API path
        operation (str): REST API operation (GET, POST, etc.) 
        parameters (str): Query parameters
    """

    # query vector DB for local data
    # query without the where_clause to include context from the User Guide PDF
    context_query = self.database.query_db(query_string,20)

    # create promt message with local context data
    message = f'Query path: "{path}"\nREST operation: {operation}\nshort description: {query_string}\n{parameters}\nUse this context delimited with XML tags:\n<context>\n{context_query}\n</context>'
    log.debug(f"===== Extending the description with:\n {message}")

    # ask LLM
    response = ollama.chat(model=self.model, messages=[
        {"role": "system",
         "content": "You are provided information of a specific REST API query path of the Cisco Catalyst Center. Describe what this query is for. Describe how this query can be used from a user perspective."},
        {"role": "user",
         "content": message}
      ]
    )

    return response['message']['content']

  def ask_llm(self,query_string,n_results_apidocs=10,n_results_apispecs=20):
    """
    Ask the LLM with the query string.
    Search for context in vectorDB

    Args:
        query_string (str): details of the REST API call
        n_results_apidocs (int): Number of documents return by vectorDB query for API docs on developer.cisco.com
        n_results_apispecs (int): Number of documents return by vectorDB query for extended API specification document
    """
    # Record the start time
    start_time = time.time()

    # context queries to vectorDB
    context_query_apidocs = self.database.query_db(query_string,n_results_apidocs,"apidocs")
    context_query_apispecs = self.database.query_db(query_string,n_results_apispecs,"apispecs")
    context = f'''Context information delimited with XML tags:\n<context>\n{context_query_apidocs}\n</context>
                  API specification context delimited with XML tags:\n<api-context>\n{context_query_apispecs}\n</api-context>'''

    question = f"\n\nUser question: '{query_string}'"

    # assemble message for LLM with context + user question
    message = context + question

    log.debug(message)

    response = ollama.chat(model=self.model, messages=[
    {
        "role": "system",
        "content": """You are the Cisco Catalyst Center REST API and Python code assistant. You provide documentation and Python code for developers.
         Always list all available query parameters from the provided context. Include the REST operation and query path.
         1. you create documentation to the specific API calls. 
         2. you create an example source code in the programming language Python using the 'requests' library.
         Tell the user if you do not know the answer. If loops or advanced code is needed, provide it.
         ###
         Every API query needs to include the header parameter 'X-Auth-Token' for authentication and authorization. This is where the access token is defined.
         If the user does not have the access token, the user needs to call the REST API query '/dna/system/api/v1/auth/token' to receive the access token. Only the API query '/dna/system/api/v1/auth/token' is using the Basic authentication scheme, as defined in RFC 7617. All other API queries need to have the header parameter 'X-Auth-Token' defined.
         ###
        """
    },{
        'role': 'user',
        'content': message,
    }
    ])

    # Calculate the total duration
    duration = time.time() - start_time
    log.info(f"The query '{query_string}' took {duration} seconds to execute.")

    return response['message']['content']