import os


from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

documents = SimpleDirectoryReader("./data").load_data()

Settings.chunk_size = 512
Settings.chunk_overlap = 50

index = VectorStoreIndex.from_documents(
    documents,
)

def retrieve_chunks(query):
    retriever = index.as_retriever(similarity_top_k=5)
    results = retriever.retrieve(query)
    return results

def retrieve(query):
    results = retrieve_chunks(query)
    for result in results:
        print(result.node.metadata["file_path"])
        print(result.node)
        print(result.score)

if __name__ == "__main__":
    while True:
        query = input("Enter a query ('q' to quit): ")
        if query == "q":
            break
        retrieve(query)