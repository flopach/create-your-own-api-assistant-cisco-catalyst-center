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
# SETTINGS
# ======================

# Select the LLM which you would like to use.
# "openai" or "ollama". You can also define the specific model below
setting_chosen_LLM = "openai"

# Do you want to extend the API specification from scratch?
# True = Your chosen LLM will generate the existing base API documentation. This can take several hours.
# False = Use the already generated JSON file (generated with GPT-3.5-turbo)
setting_full_import = False

# ======================
# Instance creations
# ======================

# set logging level
log = logging.getLogger("applogger")
logging.getLogger("applogger").setLevel(logging.DEBUG)

if setting_chosen_LLM == "openai":
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

  # trick for loader: https://docs.chainlit.io/concepts/message
  msg = cl.Message(content="")
  await msg.send()

  # if the user only types "importdata", call the import_data() function
  if message.content == "importdata":
    msg.content = await import_data()
  else:
    # else, send the user_query to the LLM
    msg.content = await ask_llm(message.content)

  await msg.update()

@cl.step
async def ask_llm(query_string):
  """
  Chainlit Step function: ask the LLM + return the result
  """
  response = LLM.ask_llm(query_string)
  return response

@cl.step
async def import_data():
  """
  Chainlit Step function: Importing data to vectorDB
  """
  # Import data from API documentation  
  datahandler.scrape_apidocs_catcenter()

  # Import data from Catalyst Center PDF User Guide
  datahandler.scrape_pdfuserguide_catcenter("data/b_cisco_catalyst_center_user_guide_237.pdf")

  # Import API Specs Document
  if setting_full_import:
    datahandler.import_apispecs_generate_new_data("data/GA-2-3-7-swagger-v1.annotated.json")
  else:
    datahandler.import_apispecs_from_json()

  return "All data imported!"