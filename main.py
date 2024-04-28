"""
Cisco Sample Code License 1.1
Author: flopach 2024
"""

from TalkToOpenAI import LLMOpenAI
from TalkToOllama import LLMOllama
from TalkToDatabase import VectorDB
from ImportData import DataHandler
import logging
import chainlit as cl

# ======================
# Instance creations
# ======================

# set logging level
log = logging.getLogger("applogger")
logging.getLogger("applogger").setLevel(logging.DEBUG)

chosen_LLM = "openai"

if chosen_LLM == "openai":
  # OpenAI: Create instance for Vector DB and LLM
  database = VectorDB("catcenter_vectors","openai","chromadb/")
  LLM = LLMOpenAI(database=database,model="gpt-3.5-turbo")
else:
  # Open Source LLM: Create instance for Vector DB and LLM
  database = VectorDB("catcenter_vectors","ollama","chromadb/")
  LLM = LLMOllama(database=database,model="llama3")

# Create DataHandler instance to import and embed data from local documents
datahandler = DataHandler(database,LLM)

# ======================
# Chainlit functions
# docs: https://docs.chainlit.io/get-started/overview
# ======================

@cl.on_chat_start
def on_chat_start():
  log.info("A new chat session has started!")


@cl.on_message
async def main(message: cl.Message):
  """
  This function is called every time a user inputs a message in the UI.
  It sends back an intermediate response from the tool, followed by the final answer.

  Args:
     message: The user's message.
  """

  if message.content == "importdata":
    response = await import_data()
  else:
    response = await ask_llm(message.content)

  # Send the final answer.
  await cl.Message(content=response).send()

@cl.step
async def ask_llm(query_string):
  """
  ask the LLM + return the result
  """
  return LLM.ask_llm(query_string)

@cl.step
async def import_data():
  """
  Importing data to vectorDB
  """
  # Import data from API documentation  
  datahandler.scrape_apidocs_catcenter()

  # Import data from Catalyst Center PDF User Guide
  datahandler.scrape_pdfuserguide_catcenter("data/b_cisco_catalyst_center_user_guide_237.pdf")

  # Import API Spec Document
  # --> Go to the function to see how the data is prepared
  datahandler.import_api_spec("data/GA-2-3-7-swagger-v1.annotated.json")
  
  return "All data imported!"