from typing import List, Dict, Optional, Tuple, Any
import os

from dotenv import load_dotenv
load_dotenv()

import pyprojroot
root_dir = pyprojroot.here()

from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader
from llama_index.core import load_index_from_storage, load_indices_from_storage
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.selectors import LLMMultiSelector
from llama_index.core.agent import FunctionCallingAgentWorker, AgentRunner
from llama_index.core.objects import ObjectIndex


class MultiDocumentRAG():
    def __init__(self, upload_dir, persist_dir, llm="gpt-3.5-turbo"):
        self.llm = OpenAI(model=llm)

        self.upload_dir = upload_dir
        self.persist_dir = persist_dir
        
        if not os.path.exists(persist_dir):
            # create new storage context
            self.storage_context = StorageContext.from_defaults()
        else:
            # load existing storage context
            self.storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        
        self.node_parser = SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )

        self._indices = {}
        self._agent = None
        self._modified = False
    
    def setup_indicies(self) -> None:
        self._load_existing_indices()

    def setup_agent(self, system_prompt: str = None) -> None:
        '''
        Setup the agent with tools from all documents.
        '''
        obj_index = ObjectIndex.from_objects(
            self._get_tools(),
            index_cls=VectorStoreIndex,
        )
        obj_retriever = obj_index.as_retriever(similarity_top_k=3)

        default_prompt = """ 
        You are an agent designed to answer queries over a set of given papers.
        Please always use the tools provided to answer a question. Do not rely on prior knowledge.
        If you do not know the answer, just say "I don't know".
        """
        
        agent_worker = FunctionCallingAgentWorker.from_tools(
            tool_retriever=obj_retriever,
            llm=self.llm,
            system_prompt=system_prompt or default_prompt,
            verbose=True
        )

        self._agent = AgentRunner(agent_worker)
    
    def query(self, query_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Query across all documents and return response with source information.
        Returns tuple of (response_text, source_chunks)
        """
        if not self._agent:
            raise ValueError("Agent not set up. Call setup_agent() first")
            
        response = self._agent.chat(query_text)

        return response

    def shutdown(self) -> None:
        '''
        Save all indices to storage
        '''
        if self._modified:
            self.storage_context.persist(persist_dir=self.persist_dir)

    def create_indices(self, files: list[str]) -> None:
        '''
        Create indices from given files in the upload folder.
        '''
        new_files = [file for file in files if file not in self._indices.keys()]
        if not new_files:
            print("No new files to create indices for")
            return
        reader = SimpleDirectoryReader(input_files=[os.path.join(self.upload_dir, file) for file in new_files], filename_as_id=True)
        for documents in reader.iter_data():
            file_name = documents[0].metadata['file_name']
            self._create_index(file_name, documents)
        self._modified = True
    
    def delete_indices(self, files: list[str]) -> None:
        '''
        Delete index and associated nodes from storage.
        NOTE: agent tools cannot be updated after agent creation
        '''
        for file in files:
            index = self._indices[file]
            for ref_doc in index.ref_doc_info.keys():
                index.delete_ref_doc(ref_doc, delete_from_docstore=True)
            index.storage_context.index_store.delete_index_struct(file)
            del self._indices[file]
        self._modified = True
    
    def _create_index(self, file: str, documents: str) -> VectorStoreIndex:
        '''
        Create index from documents.
        '''
        nodes = self.node_parser.get_nodes_from_documents(documents)
        index = VectorStoreIndex(nodes, storage_context=self.storage_context)
        index.set_index_id(file)
        self._indices[file] = index
        print(f"Created index for {file}")
        return index
    
    def _load_existing_indices(self) -> None:
        '''
        populate self._indices with EXISTING INDICES from upload directory
        '''
        files = os.listdir(self.upload_dir)
        indices = self._load_indicies(files)
        for file, index in indices.items():
            self._indices[file] = index
    
    def _load_indicies(self, files: list[str]) -> dict[str, VectorStoreIndex]:
        '''
        Given list of files, load correspdoning indices from storage.
        Can be used to load one or multiple indices.
        Files must be present in storage (Error handling not yet implemented).
        '''
        if not files:
            return {}
        indicies = {}
        for file in files:
            try:
                index = load_index_from_storage(self.storage_context, index_id=file)
                indicies[file] = index
            except Exception as e:
                print(f"Index not found for {file}: {e}")
        return indicies

    def _get_tools(self) -> list[QueryEngineTool]:
        '''
        Get tools from all indices
        '''
        tools = []
        for file, index in self._indices.items():
            tool = QueryEngineTool.from_defaults(
                query_engine=index.as_query_engine(),
                description=f"Useful for retrieving specific context related to {file}"
            )
            tools.append(tool)
        return tools
    
def main():
    UPLOAD_DIR = os.path.join(root_dir, "backend/uploads")
    PERSIST_DIR = os.path.join(root_dir, "backend/storage")

    rag = MultiDocumentRAG(UPLOAD_DIR, PERSIST_DIR)

    rag.setup_indicies()

    files = os.listdir(UPLOAD_DIR)
    rag.create_indices(files)

    rag.setup_agent()

    query = ""
    while query != "exit":
        try:
            query = input("Enter query (or 'exit' to quit): ")
            if query == "exit":
                break
                
            response = rag.query(query)
            print("\nResponse:", response)
            
            print("\nSources:")
            for idx, source in enumerate(response.source_nodes):
                print(f"\nSource {idx}:")
                print(f"Document: {source.node.node_id}")
                print(f"Text: {source.metadata['original_text']}")
                if source.score is not None:
                    print(f"Score: {source.score:.4f}")
                if source.node.metadata.get('page_label') is not None:
                    print(f"Page: {source.node.metadata['page_label']}")
            print("\n" + "="*50)
        except Exception as e:
            print(f"Error: {e}")
    
    rag.shutdown()
    print("Goodbye!")

if __name__ == "__main__":
    main()