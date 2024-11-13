import os

os.environ['OPENAI_API_KEY'] = "sk-..." # set OpenAI API key

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.llms.openai import OpenAI
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.workflow import (
    Context,
    Workflow,
    StartEvent,
    StopEvent,
    Event,
    step,
)
from llama_index.core.schema import NodeWithScore

class RetrieverEvent(Event):
    nodes: list[NodeWithScore]

class RAGWorkflow(Workflow):
    def __init__(self):
        # TODO: implement vector store

        # create sentence window node parser
        self.node_parser = SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )

        # create vector store index
        self.index = VectorStoreIndex([])

        # create set of document ids
        self.documents = set()

        super().__init__()

    @step
    async def insert(self, ctx: Context, event: StartEvent) -> StopEvent | None:
        directory = event.get("directory")
        if not directory:
            return None
        
        # load txt files from data folder
        documents = SimpleDirectoryReader(directory, filename_as_id=True).load_data()

        # parse documents using node parser
        nodes = self.node_parser.get_nodes_from_documents(documents)

        # add document ids to set
        for doc in documents:
            self.documents.add(doc.doc_id)
        
        print(self.documents)

        # add nodes to index
        self.index.insert_nodes(nodes)
        print("Documents inserted into index.")

        return StopEvent()
    
    @step
    async def delete(self, ctx: Context, event: StartEvent) -> StopEvent | None:
        filenames = event.get("filenames")
        if not filenames:
            return None
        
        # delete nodes corresponding to documents
        for filename in filenames:
            if filename not in self.documents:
                print(f"Document {filename} not found in index.")
                continue
            await self.index.adelete_ref_doc(filename)
            self.documents.remove(filename)
            print(f"Document {filename} deleted from index.")
        
        return StopEvent()

    @step
    async def retrieve(self, ctx: Context, event: StartEvent) -> RetrieverEvent | None:
        query = event.get("query")
        if not query:
            return None
        
        # set query in global context
        await ctx.set("query", query)

        # create retriever
        retriever = self.index.as_retriever(
            similarity_top_k=5,
            node_postprocessors=[
                MetadataReplacementPostProcessor(target_metadata_key="window")
            ],
        )

        # retrieve nodes
        nodes = await retriever.aretrieve(query)
        print(f"Retrieved {len(nodes)} nodes.")

        return RetrieverEvent(nodes=nodes)
    
    @step
    async def generate(self, ctx: Context, event: RetrieverEvent) -> StopEvent:
        query = await ctx.get("query", default=None)
        nodes = event.nodes

        # TODO: generate llm response

        return StopEvent(result=nodes)

async def test():
    workflow = RAGWorkflow()

    # insert documents
    await workflow.run(directory="./data")

    # retrieve nodes
    results = await workflow.run(query="What is Tesla model S?")

    for res in results:
        print(res.node.metadata["original_text"])
        print(res.score)

    # delete documents
    await workflow.run(filenames=["FILE_PATH_HERE"]) # list absolute paths of documents to delete

    # retrieve nodes
    results = await workflow.run(query="What is Tesla model S?")

    for res in results:
        print(res.node.metadata["original_text"])
        print(res.score)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())