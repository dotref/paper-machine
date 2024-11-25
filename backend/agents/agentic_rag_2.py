from typing import List, Dict, Optional, Tuple, Any, Callable
import os
import re
from dotenv import load_dotenv

import pyprojroot
root_dir = pyprojroot.here()

import nest_asyncio
from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader, Settings
from llama_index.core import load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter, SentenceWindowNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.selectors import LLMMultiSelector
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.agent.openai import OpenAIAgent


class MultiDocumentRAG():
    def __init__(self, upload_dir, persist_dir, llm="gpt-3.5-turbo", embedding_model="text-embedding-ada-002"):
        load_dotenv()
        nest_asyncio.apply()
        
        Settings.llm = OpenAI(model=llm)
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)

        self.upload_dir = upload_dir
        self.persist_dir = persist_dir
        
        if not os.path.exists(persist_dir):
            # create new storage context
            self.storage_context = StorageContext.from_defaults()
        else:
            # load existing storage context
            self.storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        
        def splitter() -> Callable[[str], List[str]]:
            splitter = SentenceSplitter(chunk_size=60, chunk_overlap=13)
            def split(text: str) -> List[str]:
                return splitter.split_text(text)
            return split

        self.node_parser = SentenceWindowNodeParser.from_defaults(
            sentence_splitter=splitter(),
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

        default_prompt = """ 
        You are an agent designed to answer queries over a set of given papers.
        Please always use the tools provided to answer a question. Do not rely on prior knowledge.
        If you do not know the answer, just say "I don't know".
        """
        self._agent = OpenAIAgent.from_tools(
            tools=self._get_tools(),
            system_prompt=system_prompt or default_prompt,
            llm=Settings.llm,
            verbose=True
        )
    
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
        Index has to be loaded first
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
                print(f"Loaded index for {file}")
            except Exception as e:
                print(f"Index not found for {file}: {e}")
        return indicies

    def _get_tools(self) -> list[QueryEngineTool]:
        '''
        Get tools from all indices
        '''
        tools = []
        for file, index in self._indices.items():
            query_engine = index.as_query_engine(
                node_postprocessors=[
                    MetadataReplacementPostProcessor(target_metadata_key="window")
                ],
            )

            # use query engine to generate a description and title
            name = query_engine.query("Please provide a title under 64 characters for this document.").response
            description = query_engine.query("Please provide a short description of this document.").response

            # replace characters that are not alphanumeric
            name = re.sub(r'\W+', '_', name)

            # if title is longer than 64 characters, truncate it
            if len(name) > 64:
                name = name[:64]

            print(f"Name: {name}")
            print(f"Description: {description}")

            tool = QueryEngineTool(
                query_engine=query_engine,
                metadata=ToolMetadata(
                    name=name,
                    description=description
                )
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