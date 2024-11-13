import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
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
from llama_index.core.tools import QueryEngineTool
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.base.response.schema import Response

class RAGManager:
    def __init__(
        self,
        data_dir: str = "data/",
        vector_store_dir: str = "stored_vector_embeddings",
        summary_store_dir: str = "stored_summary_embeddings",
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        llm_model: str = "gpt-3.5-turbo",
        embedding_model: str = "text-embedding-ada-002"
    ):
        """Initialize RAG Manager with configuration parameters."""
        load_dotenv()
        
        # Configure settings
        Settings.llm = OpenAI(model=llm_model)
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        
        self.data_dir = data_dir
        self.vector_store_dir = vector_store_dir
        self.summary_store_dir = summary_store_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize as None
        self.documents = None
        self.nodes = None
        self.vector_index = None
        self.summary_index = None
        self.query_engine = None
        
        # Node mapping for source tracking
        self.node_mapping = {}
    
    def load_documents(self) -> None:
        """Load documents from the data directory."""
        self.documents = SimpleDirectoryReader(input_dir=self.data_dir).load_data()
        print(f"\nLoaded {len(self.documents)} documents from {self.data_dir}/")
        
        # Create nodes from documents
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
                'metadata': node.metadata
            }
        
        print(f"Parsed {len(self.nodes)} nodes from documents")
    
    def build_indices(self) -> None:
        """Build vector and summary indices from nodes."""
        if self.nodes is None:
            raise ValueError("Documents not loaded. Call load_documents() first.")
        
        # https://docs.llamaindex.ai/en/stable/understanding/indexing/indexing/
        # https://docs.llamaindex.ai/en/stable/module_guides/indexing/index_guide/
        # Summary index simply stores Nodes as a sequential chain.
        # Vector index takes documents as input and then creates vector embeddings of the text of every node
        self.vector_index = VectorStoreIndex(self.nodes)
        self.summary_index = SummaryIndex(self.nodes)
        
        # Save indices
        self.save_indices()
    
    def save_indices(self) -> None:
        """Save indices to disk."""
        if self.vector_index and self.summary_index:
            self.vector_index.storage_context.persist(persist_dir=self.vector_store_dir)
            self.summary_index.storage_context.persist(persist_dir=self.summary_store_dir)
            
            # Save node mapping
            import pickle
            with open(os.path.join(self.vector_store_dir, 'node_mapping.pkl'), 'wb') as f:
                pickle.dump(self.node_mapping, f)
    
    def load_indices(self) -> None:
        """Load indices from disk."""
        if os.path.exists(self.vector_store_dir) and os.path.exists(self.summary_store_dir):
            self.vector_index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=self.vector_store_dir)
            )
            self.summary_index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=self.summary_store_dir)
            )
            
            # Load node mapping
            import pickle
            with open(os.path.join(self.vector_store_dir, 'node_mapping.pkl'), 'rb') as f:
                self.node_mapping = pickle.load(f)
            
            print("Loaded indices from disk")
        else:
            raise FileNotFoundError("Index storage directories not found")
    
    def setup_query_engine(self) -> None:
        """Setup the router query engine with vector and summary tools."""
        if not (self.vector_index and self.summary_index):
            raise ValueError("Indices not initialized. Build or load indices first.")
        
        summary_query_engine = self.summary_index.as_query_engine(
            response_mode="tree_summarize"
        )
        vector_query_engine = self.vector_index.as_query_engine()
        
        summary_tool = QueryEngineTool.from_defaults(
            query_engine=summary_query_engine,
            description="Useful for summarization questions related to the documents"
        )
        
        vector_tool = QueryEngineTool.from_defaults(
            query_engine=vector_query_engine,
            description="Useful for retrieving specific context from the documents"
        )
        
        self.query_engine = RouterQueryEngine(
            selector=LLMSingleSelector.from_defaults(),
            query_engine_tools=[summary_tool, vector_tool],
            verbose=True
        )
    
    def query(self, query_text: str) -> Response:
        """Query the documents and return response."""
        if self.query_engine is None:
            raise ValueError("Query engine not set up. Call setup_query_engine() first.")
        return self.query_engine.query(query_text)
    
    def get_source_documents(self, response: Response) -> List[Dict]:
        """Get source documents for a given response."""
        sources = []
        if hasattr(response, 'source_nodes'):
            for source_node in response.source_nodes:
                node_id = source_node.node.node_id
                if node_id in self.node_mapping:
                    sources.append({
                        'text': self.node_mapping[node_id]['text'],
                        'metadata': self.node_mapping[node_id]['metadata'],
                        'score': source_node.score
                    })
        return sources

def main():
    # Initialize RAG manager
    rag = RAGManager()
    
    # Either load new documents and build indices
    rag.load_documents()
    # rag.build_indices()
    
    # Or load existing indices
    rag.load_indices()
    
    # Setup query engine
    rag.setup_query_engine()
    
    # Interactive query loop
    query = ""
    while query != "exit":
        query = input("Enter a query (type 'exit' to quit): ")
        if query == "exit":
            break
            
        response = rag.query(query)
        print("\nResponse:", str(response))
        
        print("\nSource Documents:")
        sources = rag.get_source_documents(response)
        for idx, source in enumerate(sources, 1):
            print(f"\nSource {idx}:")
            print(f"Text: {source['text'][:200]}...")
            print(f"File: {source['metadata'].get('file_name', 'Unknown')}")
            if source['score'] is not None:
                print(f"Score: {source['score']:.4f}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    main()