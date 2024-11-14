import os
from dotenv import load_dotenv
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader
from llama_index.core import load_index_from_storage, load_indices_from_storage
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.selectors import LLMMultiSelector

UPLOAD_DIR = "./data"
PERSIST_DIR = "./storage"

node_parser = SentenceWindowNodeParser.from_defaults(
    window_size=3,
    window_metadata_key="window",
    original_text_metadata_key="original_text",
)

def create_index(file: str, storage_context: StorageContext) -> VectorStoreIndex:
    '''
    Create index from given file in the upload folder.
    Remember to persist storage context.
    '''
    document = SimpleDirectoryReader(input_files=[os.path.join(UPLOAD_DIR, file)]).load_data()[0]
    document.doc_id = document.metadata["file_name"]
    nodes = node_parser.get_nodes_from_documents([document])

    index = VectorStoreIndex(nodes, storage_context=storage_context)
    index.set_index_id(document.doc_id)
    
    return index

def load_indicies(files: list[str]) -> list[VectorStoreIndex]:
    '''
    Given list of files, load correspdoning indices from storage.
    Can be used to load one or multiple indices.
    Files must be present in storage (Error handling not yet implemented).
    '''
    print(files)
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    indicies = load_indices_from_storage(
        storage_context, index_ids=files
    )
    return indicies

def delete_index(file, storage_context: StorageContext):
    '''
    Delete index and associated nodes from storage.
    '''
    index = load_index_from_storage(storage_context, index_id=file)
    for ref_doc in index.ref_doc_info.keys():
        index.delete_ref_doc(ref_doc, delete_from_docstore=True)
    index.storage_context.index_store.delete_index_struct(file)

def init():
    '''
    Initialize storage context and create index for each uploaded file.
    Persists storage context locally in PERSIST_DIR.
    '''
    # create new storage context
    storage_context = StorageContext.from_defaults()

    # load txt files from data folder
    documents = SimpleDirectoryReader(UPLOAD_DIR).load_data()

    # parse each document and create a separate index
    for document in documents:
        document.doc_id = document.metadata["file_name"]
        nodes = node_parser.get_nodes_from_documents([document])

        index = VectorStoreIndex(nodes, storage_context=storage_context)
        index.set_index_id(document.doc_id)

    # persist storage context
    storage_context.persist(persist_dir=PERSIST_DIR)

if __name__ == '__main__':
    '''
    Demo to build index for each uploaded file, persist indices, and load indices.
    and route queries to the appropriate index query engine.
    '''
    if not os.path.exists(PERSIST_DIR):
        init()

    # specify selected files, currently lists all files in upload folder
    # eventually want to support dynamic selection of documents to reference for query.
    files = os.listdir(UPLOAD_DIR)

    # load indices
    indicies = load_indicies(files)

    # initialize query engines
    tools = []
    for file, index in zip(files, indicies):
        tool = QueryEngineTool.from_defaults(
            query_engine=index.as_query_engine(),
            description=f"Useful for retrieving specific context related to {file}", # basic description, can replace with summary of document
        )
        tools.append(tool)

    # initialize router query engine, can try different combinations of llms and selectors
    query_engine = RouterQueryEngine(
        llm=OpenAI(model="gpt-3.5-turbo"),
        selector=LLMMultiSelector.from_defaults(), 
        query_engine_tools=tools,
        verbose=True
    )

    # run query engine
    query1 = "What is iPhone?"
    print(query1)
    response = query_engine.query(query1)

    print(response)
    print(f'source node 0: {response.source_nodes[0].metadata["original_text"]}')
    print(f'relevance: {response.source_nodes[0].score}')

    # hello kitty is not in the data but llm will still produce a response based on prior knowledge
    # if we don't want llm to produce a response in the absence of data, can try strategies such as:
        # set a relevance threshold
        # use a filtering strategy to determine whether source nodes are relevant to the query
        # prompt engineer so llm doesn't produce a response
    query2 = "who is Hello Kitty?"
    print(query2)
    response = query_engine.query(query2)

    print(response)
    print(f'source node 0: {response.source_nodes[0].metadata["original_text"]}')
    print(f'relevance: {response.source_nodes[0].score}')
