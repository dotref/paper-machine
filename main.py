import os

import qdrant_client
from llama_index.core import SimpleDirectoryReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.indices import MultiModalVectorStoreIndex
from llama_index.core.schema import ImageNode, ImageDocument

from llama_index.multi_modal_llms.openai import OpenAIMultiModal

# Create a local Qdrant vector store
client = qdrant_client.QdrantClient(path="qdrant_db")

text_store = QdrantVectorStore(client=client, collection_name="text_collection")
image_store = QdrantVectorStore(client=client, collection_name="image_collection")
storage_context = StorageContext.from_defaults(vector_store=text_store, image_store=image_store)

# Create the MultiModal index
documents = SimpleDirectoryReader("./data_wiki/").load_data() # loads the data as documents along with their metadata
# create the index from the documents and storage context
index = MultiModalVectorStoreIndex.from_documents(documents, storage_context=storage_context) # this is the thing that costs money i think

# Save it
# index.storage_context.persist(persist_dir="./storage")

# # Load it
from llama_index.core import load_index_from_storage

# storage_context = StorageContext.from_defaults(vector_store=text_store, persist_dir="./storage")
# index = load_index_from_storage(storage_context, image_store=image_store)


def retrieve_documents(text_query: str = None, image_query: str = None):
    '''
    Retrieve relevant documents given text query.
    '''
    if not text_query and not image_query:
        return [], []
    
    retrieved_images = set()
    retrieved_texts = set()
    retriever = index.as_retriever(similarity_top_k=3, image_similarity_top_k=5)
    
    if text_query:
        retrieval_results = retriever.retrieve(text_query)

        for res in retrieval_results:
            if isinstance(res.node, ImageNode):
                retrieved_images.add(res.node.metadata["file_path"])
            else:
                retrieved_texts.add(res.node.get_text())

    if image_query:
        retrieval_results = retriever.image_to_image_retrieve(image_query)
        for res in retrieval_results:
            if isinstance(res.node, ImageNode):
                retrieved_images.add(res.node.metadata["file_path"])
            else:
                retrieved_texts.add(res.node.get_text())

    return retrieved_images, retrieved_texts

def process_prompt(prompt: str):
    '''
    gpt-4o RAG
    '''
    # TODO: transform prompt to query?
    query = prompt
    retrieved_images, retrieved_texts = retrieve_documents(text_query=query)

    image_documents = [ImageDocument(image_path=path) for path in retrieved_images]

    llm = OpenAIMultiModal(model="gpt-4o", api_key=os.environ.get("OPENAI_API_KEY"), max_new_tokens=1500)
    response = llm.complete(prompt=prompt, image_documents=image_documents)

    # Can also use index as query engine for rag
    # query_engine = index.as_query_engine(llm=llm, image_qa_template=qa_tmpl)

    return response

if __name__ == "__main__":
    # run data.py to ensure data folder is populated before creating the index
    while True:
        prompt = input("Enter prompt (quit to exit): ")
        if prompt.lower() == "quit":
            break
        try:
            response = process_prompt(prompt)
            print(response)
        except Exception as e:
            print(f"Error: {e}")
