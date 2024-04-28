"""
Cisco Sample Code License 1.1
Author: flopach 2024
"""
import chromadb
import os
import logging
log = logging.getLogger("applogger")

class VectorDB:
  def __init__(self, collection_name, embeddings_function = "openai", database_path = "chromadb/"):
    """
    Create new VectorDB instance

    Args:
        collection_name (str): Name of the collectiong
        embeddings_function (str): "openai" or "ollama"
        database_path (str): persistent storage for vectorDB
    """

    # define chromadb client
    self.chromadb_client = chromadb.PersistentClient(path=database_path)

    # set embeddings function
    # different for each chosen LLM
    if embeddings_function == "openai":
      self.embeddings_function = chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv('OPENAI_API_KEY'),
                model_name="text-embedding-3-small"
            )
    elif embeddings_function == "ollama":
      self.embeddings_function =  chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
    
    # set collection
    self.collection = self.chromadb_client.get_or_create_collection(name=collection_name,embedding_function=self.embeddings_function)

  def query_db(self, query_string, n_results, where_clause=None):
    """
    Query the vector DB

    Args:
        query_string (str): specific query string
        n_results
        where_clause (str): Option to define WHERE clause for vectorDB query:
                            default --> None
                            apidocs --> {"doc_type": "apidocs"}
                            apispecs --> {"doc_type": "apispecs"}
    """

    # define vectorDB search
    # docs: https://docs.trychroma.com/reference/Collection#query

    if where_clause == "apidocs":
      where_clause = {"doc_type": "apidocs"}
    elif where_clause == "apispecs":
      where_clause = {"doc_type": "apispecs"}

    results = self.collection.query(
      query_texts=[query_string],
      n_results=n_results,
      where=where_clause
    )

    # Display queried documents
    log.debug(f"Queried documents: {results["metadatas"]}")
    log.debug(f"Queried distances: {results["distances"]}")

    return results["documents"]
  
  def collection_add(self,documents,ids,metadatas=None):
    """
    Add to collection

    Args:
        documents (dict): list of chunked documents
        ids (dict): list of IDs
        metadatas (dict): list of metadata
    """
    r = self.collection.add(
      documents=documents,
      ids=ids,
      metadatas=metadatas,
    )
    if r != None:
      log.warning(f"{ids} returned NOT None...")