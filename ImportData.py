"""
Cisco Sample Code License 1.1
Author: flopach 2024
"""
import json
import glob
import fitz
import tiktoken
from bs4 import BeautifulSoup
import requests
import logging
log = logging.getLogger("applogger")

class DataHandler:
    def __init__(self, database, LLM):
        self.llm = LLM
        self.database = database

    def scrape_apidocs_catcenter(self):
        """
        Scrape developer.cisco.com Catalyst Center API docs        
        """
        base_url = "https://developer.cisco.com/docs/dna-center/"

        docs_list = [
            "overview",
            "getting-started",
            "api-quick-start",
            "asynchronous-apis",
            "authentication-and-authorization",
            "command-runner",
            "credentials",
            "device-onboarding",
            "device-provisioning",
            "devices",
            "discovery",
            "events",
            "global-ip-pool",
            "health-monitoring",
            "path-trace",
            "rma-device-replacement",
            "reports",
            "software-defined-access-sda",
            "sites",
            "swim",
            "topology"
        ]
        
        for doc in docs_list:
            try:
                r = requests.get(base_url+doc)
                soup = BeautifulSoup(r.content, 'html.parser')
                chunks = self._chunk_text(soup.get_text(),512)

                #log.info(chunks)

                self.database.collection_add(
                    documents=chunks,
                    ids=[f"{doc}_{x}" for x in range(len(chunks))],
                    metadatas=[{ "doc_type" : "apidocs" } for x in range(len(chunks))]
                )

                log.info(f"Scraped data from {base_url+doc}")

            except Exception as e:
                log.error(f"Error when requesting data from {base_url+doc}! Error: {e}")
        
        log.info(f"=== Done with api docs scraping ===")

    
    def scrape_pdfuserguide_catcenter(self,filepath):
        """
        Scrape Catalyst Center PDF User Guide
        """
        try:
            log.info(f"=== Start: Chunking + embedding PDF User Guide file ===")
            with fitz.open(filepath) as doc:  # open document
                content = chr(12).join([page.get_text() for page in doc])

                chunks = self._chunk_text(content,512)

                self.database.collection_add(
                    documents=chunks,
                    ids=[f"user_guide_{x}" for x in range(len(chunks))]
                )
            log.info(f"=== End: Chunking + embedding PDF User Guide file ===")
        except Exception as e:
            log.error(f"Error when reading PDF! Error: {e}")

    def import_api_spec(self,filepath):
        """
        This function prepares the data from the API specification.

        1. Only specific data is extracted from the OpenAPI document
        2. Based on the information within the vectorDB (API docs, User Guide) an extended description is created via the LLM
        3. The newly created information is saved in the vectorDB

        Args:
            filepath (str): path to file
        """

        json_document = {
            "documents" : [],
            "ids" : [],
            "metadatas" : []
        }

        # open openAPI specs file
        with open(filepath, "r") as f:
            dict = json.load(f)
            log.info(f"Opened API Specification")

            p = 1
            for path in dict["paths"]:
                """ loop through each API path in the document """
                path_dict = dict["paths"][path]
                log.info(f"=== STATUS: {p} out of {len(dict["paths"])} paths ===")
                p += 1
                
                for operation in path_dict:
                    """ loop through each REST operation """
                    summary = path_dict[operation]["summary"]
                    operationId = path_dict[operation]["operationId"]
                    description = path_dict[operation]["description"]
                    first_tag = path_dict[operation]["tags"][0]

                    # if parameters are defined, list them
                    if len(path_dict[operation]["parameters"]) != 0:
                        parameters = ""
                        for parameter in path_dict[operation]["parameters"]:
                            """ loop through each parameters """
                            p_name = parameter["name"]
                            p_description = parameter["description"]

                            p_in = f"The query parameters should be used in the {parameter["in"]}. "

                            p_default_value = ""
                            if "default" in parameter:
                                if parameter["default"] != "":
                                    p_default_value = f"The default value is '{parameter["default"]}'. "

                            p_required = ""
                            if "required" in parameter:
                                p_required = "This query parameter is required. "
                            else:
                                p_required = "This query parameter is not required. "
                            
                            parameters += f"- {p_name}: {p_description}. {p_in}{p_default_value}{p_required}\n"
                        parameters = f"REST API query parameters:\n{parameters}\n"
                    else:
                        parameters = ""
                    
                    # Generate extended description for this API Call
                    ai_description = self.llm.extend_api_description(f"{summary}.{description}",path,operation,parameters)

                    # === Assemble all information ===

                    # Create for each API path an extended documentation
                    # chunk the document into several parts
                    content = f"""{ai_description}\n\nREST API query information delimited with XML tags\n<api-query>\nAPI query path:{path}\nREST operation:{operation}\n{parameters}</api-query>"""
                    document_chunks = self._chunk_text(content,512)

                    # create for each document chunk ids. Use operationId as base id.
                    ids = [f"{operationId}_{x}" for x in range(len(document_chunks))]

                    # create metadata for each document chunk
                    metadatas = [{ "summary": summary, "tag" : first_tag, "doc_type" : "apispecs" } for x in range(len(document_chunks))]

                    #logging chunks
                    #log.debug(document_chunks)

                    # === put all information into vectorDB ===

                    # add into vectordb
                    self.database.collection_add(
                        documents=document_chunks,
                        ids=ids,
                        metadatas=metadatas
                    )

                    # === put all information into a dict which will be saved later to JSON ===

                    json_document["documents"].append(content)
                    json_document["ids"].append(operationId)
                    json_document["metadatas"].append({ "summary": summary, "tag" : first_tag, "doc_type" : "apispecs" })

                    log.info(f"=== NEW document added:\n{content} ===")
        
        # === put all information into JSON (optional, plain-text saving) ===

        with open("data/extended_apispecs_documentation.json", "w") as f:
            json.dump(json_document, f)

        log.info(f"=== Extended, chunked, embedded the openapi specification into the vectorDB ===")
    
    def _chunk_text(self,content,chunk_size):
        """
        The most basic method: Chunking by characters
        + Replacing the new line character with a white space
        + Removing any leading and trailing whitespaces

        Args:
            content (str): string to chunk
            chunk_size (int): number of characters when to cut
        """
        chunks = [content[i:i + chunk_size].replace("\n"," ").strip() for i in range(0, len(content), chunk_size)]
        return chunks