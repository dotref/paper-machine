from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import os
import pickle
from dotenv import load_dotenv
import nest_asyncio

from llama_index.core import (
    Document, 
    VectorStoreIndex,
    SummaryIndex,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.tools import QueryEngineTool, FunctionTool
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.objects import ObjectIndex
from llama_index.core.agent import FunctionCallingAgentWorker, AgentRunner

class DocumentTool:
    """Manages tools and indices for a single document."""
    
    def __init__(
        self,
        file_path: str,
        name: str,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
    ):
        self.file_path = file_path
        self.name = name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.documents = None
        self.nodes = None
        self.vector_index = None
        self.summary_index = None
        self.node_mapping = {}
        
    def load_and_index(self) -> None:
        """Load document and create indices."""
        self.documents = SimpleDirectoryReader(input_files=[self.file_path]).load_data()
        splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        self.nodes = splitter.get_nodes_from_documents(self.documents)
        
        # Create node mapping
        for idx, node in enumerate(self.nodes):
            self.node_mapping[node.node_id] = {
                'index': idx,
                'text': node.text,
                'metadata': {
                    **node.metadata,
                    'document_name': self.name
                }
            }
            # Also set the metadata in the node itself
            node.metadata['document_name'] = self.name
        self.vector_index = VectorStoreIndex(self.nodes)
        self.summary_index = SummaryIndex(self.nodes)
        
    def get_tools(self) -> Tuple[FunctionTool, QueryEngineTool]:
        """Create and return vector and summary tools."""
        def vector_query(
            query: str,
            page_numbers: Optional[List[str]] = None
        ) -> str:
            page_numbers = page_numbers or []
            metadata_dicts = [
                {"key": "page_label", "value": p} for p in page_numbers
            ]
            
            query_engine = self.vector_index.as_query_engine(
                similarity_top_k=2,
            )
            response = query_engine.query(query)
            return response
        
        vector_tool = FunctionTool.from_defaults(
            name=f"vector_tool_{self.name}",
            fn=vector_query
        )
        
        summary_query_engine = self.summary_index.as_query_engine(
            response_mode="tree_summarize",
            use_async=True,
        )
        
        summary_tool = QueryEngineTool.from_defaults(
            name=f"summary_tool_{self.name}",
            query_engine=summary_query_engine,
            description=f"Useful for summarization questions related to {self.name}"
        )
        
        return vector_tool, summary_tool
    
    def get_source_chunk(self, node_id: str) -> Dict[str, Any]:
        """Retrieve original chunk and metadata given node ID."""
        return self.node_mapping.get(node_id, None)

class MultiDocumentRAG:
    """Manages RAG operations across multiple documents."""
    
    def __init__(
        self,
        llm_model: str = "gpt-3.5-turbo",
        embedding_model: str = "text-embedding-ada-002"
    ):
        load_dotenv()
        nest_asyncio.apply()
        
        Settings.llm = OpenAI(model=llm_model)
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        
        self.doc_tools: Dict[str, DocumentTool] = {}
        self.agent = None
        self.obj_index = None
        
    def add_document(
        self,
        file_path: str,
        name: str,
        chunk_size: int = 1024,
        chunk_overlap: int = 128
    ) -> None:
        """Add a new document to the system."""
        doc_tool = DocumentTool(
            file_path=file_path,
            name=name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        doc_tool.load_and_index()
        self.doc_tools[name] = doc_tool
        
    def setup_agent(self, system_prompt: Optional[str] = None) -> None:
        """Setup the agent with tools from all documents."""
        if not self.doc_tools:
            raise ValueError("No documents added yet")
        
        # Collect all tools
        all_tools = []
        for doc_tool in self.doc_tools.values():
            vector_tool, summary_tool = doc_tool.get_tools()
            all_tools.extend([vector_tool, summary_tool])
        
        # Create object index for tool retrieval
        self.obj_index = ObjectIndex.from_objects(
            all_tools,
            index_cls=VectorStoreIndex,
        )
        obj_retriever = self.obj_index.as_retriever(similarity_top_k=3)
        
        # Setup agent
        default_prompt = """ \
        You are an agent designed to answer queries over a set of given papers.
        Please always use the tools provided to answer a question. Do not rely on prior knowledge.\
        """
        
        agent_worker = FunctionCallingAgentWorker.from_tools(
            tool_retriever=obj_retriever,
            llm=Settings.llm,
            system_prompt=system_prompt or default_prompt,
            verbose=True
        )
        self.agent = AgentRunner(agent_worker)
    
    def query(self, query_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Query across all documents and return response with source information.
        Returns tuple of (response_text, source_chunks)
        """
        if not self.agent:
            raise ValueError("Agent not set up. Call setup_agent() first")
            
        response = self.agent.chat(query_text)
        
        # Extract source information
        source_chunks = []
        if hasattr(response, 'source_nodes'):
            for source_node in response.source_nodes:
                node_id = source_node.node.node_id
                doc_name = source_node.metadata.get('document_name')
                if doc_name in self.doc_tools:
                    chunk_info = self.doc_tools[doc_name].get_source_chunk(node_id)
                    if chunk_info:
                        source_chunks.append({
                            **chunk_info,
                            'score': source_node.score
                        })
        
        return str(response), source_chunks

def main():
    # Initialize
    rag = MultiDocumentRAG()
    
    # Add documents
    papers = [
        ("batman.txt", "Batman"),
        ("BTS.txt", "BTS"),
        ("iPhone.txt", "iPhone")
    ]
    
    for file_path, name in papers:
        rag.add_document(file_path, name)
    
    # Setup agent
    rag.setup_agent()
    
    # Interactive query loop
    query = ""
    while query != "exit":
        query = input("Enter query (or 'exit' to quit): ")
        if query == "exit":
            break
            
        response, sources = rag.query(query)
        print("\nResponse:", response)
        
        print("\nSources:")
        for idx, source in enumerate(sources, 1):
            print(f"\nSource {idx}:")
            print(f"Document: {source['metadata']['document_name']}")
            print(f"Text: {source['text'][:200]}...")
            if source["score"] is not None:
                print(f"Score: {source['score']:.4f}")
            if 'page_label' in source['metadata']:
                print(f"Page: {source['metadata']['page_label']}")
        print("\n" + "="*50)

if __name__ == "__main__":
    main()