"""
Cisco Sample Code License 1.1
Author: flopach 2024
"""
from openai import OpenAI
import time
import logging
log = logging.getLogger("applogger")

class LLMOpenAI:
  def __init__(self, database, model = "gpt-3.5-turbo"):
    self.client = OpenAI()
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
    context_query = self.database.query_db(query_string,10)

    # create promt message with local context data
    message = f'Query path: "{path}"\nREST operation: {operation}\nshort description: {query_string}\n{parameters}\nUse this context delimited with XML tags:\n<context>\n{context_query}\n</context>'
    log.debug(f"=== Extending the description with: ===\n {message}")

    # ask GPT
    completion = self.client.chat.completions.create(
      model=self.model,
      temperature=0.8,
      messages=[
        {"role": "system", "content": "You are provided information of a specific REST API query path of the Cisco Catalyst Center. Describe what this query is for in detail. Describe how this query can be used from a user perspective."},
        {"role": "user", "content": message}
      ]
    )

    return completion.choices[0].message.content

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

    message = context + question

    log.debug(message)

    completion = self.client.chat.completions.create(
      model=self.model,
      temperature=0.8,
      messages=[
        { "role": "system",
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
        },
        {"role": "user", "content": message}
      ]
    )

    # Calculate the total duration
    duration = round(time.time() - start_time, 2)
    exec_duration = f"The query '{query_string}' took **{duration} seconds** to execute."
    log.info(exec_duration)

    return completion.choices[0].message.content+"\n\n"+exec_duration