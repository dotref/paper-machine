from typing import List, Dict, Optional, Tuple, Any, Callable, Union
import os
import re
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

import pyprojroot
root_dir = pyprojroot.here()

from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader, Settings
from llama_index.core import load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter, SentenceWindowNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.postprocessor import MetadataReplacementPostProcessor, SentenceTransformerRerank
from llama_index.agent.openai import OpenAIAgent

from autogen import ConversableAgent, UserProxyAgent, Agent, GroupChat, GroupChatManager


class MultiDocumentRAG():
    def __init__(self, upload_dir, persist_dir, llm="gpt-3.5-turbo", embedding_model="text-embedding-ada-002"):
        if not os.path.exists(upload_dir):
            raise ValueError(f"Upload directory {upload_dir} does not exist")
        
        if not os.path.exists(persist_dir):
            raise ValueError(f"Persist directory {persist_dir} does not exist")

        self.upload_dir = upload_dir
        self.persist_dir = persist_dir
        
        if os.listdir(persist_dir):
            try:
                self.storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            except Exception as e:
                raise ValueError(f"Failed to load storage context from {persist_dir}")
        else:
            print(f"Creating new storage context at {persist_dir}")
            self.storage_context = StorageContext.from_defaults()

        load_dotenv()
        
        Settings.llm = OpenAI(model=llm)
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        
        def splitter() -> Callable[[str], List[str]]:
            splitter = SentenceSplitter(chunk_size=64, chunk_overlap=16)
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
        self._tools = {}
        self._modified = False
    
    def setup_indicies(self) -> None:
        '''
        Setup indicies for documents with existing indices in the upload directory.
        '''
        print("Setting up indicies...")
        files = os.listdir(self.upload_dir)
        indices = self._load_indicies(files)
        for file, index in indices.items():
            self._indices[file] = index


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
            print("Saving indices to storage...")
            self.storage_context.persist(persist_dir=self.persist_dir)


    def create_indices(self) -> None:
        '''
        Create indices from given files in the upload folder.
        '''
        uploads = os.listdir(self.upload_dir)
        new_files = [file for file in uploads if file not in self._indices.keys()]
        if not new_files:
            print("No new files to create indices for")
            return
        
        reader = SimpleDirectoryReader(input_files=[os.path.join(self.upload_dir, file) for file in new_files], filename_as_id=True)
        for documents in reader.iter_data():
            file_name = documents[0].metadata['file_name']
            self._create_index(file_name, documents)
        self._modified = True
    

    def delete_indices(self) -> None:
        '''
        Delete index and associated nodes from storage.
        Index has to be loaded first
        NOTE: agent tools cannot be updated after agent creation, you must call setup_agent again
        '''
        uploads = os.listdir(self.upload_dir)
        files_to_delete = [file for file in self._indices.keys() if file not in uploads]
        if not files_to_delete:
            print("No indices to delete")
            return

        for file in files_to_delete:
            index = self._indices[file]
            for ref_doc in index.ref_doc_info.keys():
                index.delete_ref_doc(ref_doc, delete_from_docstore=True)
            index.storage_context.index_store.delete_index_struct(file)
            del self._indices[file]

            if file in self._tools:
                del self._tools[file]

            print(f"Deleted index for {file}")
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


    def _load_indicies(self, files: list[str]) -> dict[str, VectorStoreIndex]:
        '''
        Given list of files, load correspdoning indices from storage.
        Can be used to load one or multiple indices.
        Files must be present in storage (Error handling not yet implemented).
        '''
        indicies = {}

        if not files:
            return indicies
        
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

            if file in self._tools:
                tools.append(self._tools[file])
                continue

            query_engine = index.as_query_engine(
                node_postprocessors=[
                    MetadataReplacementPostProcessor(target_metadata_key="window"),
                    SentenceTransformerRerank(model="cross-encoder/ms-marco-MiniLM-L-2-v2", top_n=3)
                ],
            )

            # use query engine to generate a name and description
            name = query_engine.query("Provide a name for this document. The name must be under 40 characters. Return only the name in your response.").response
            description = query_engine.query("Provide a short summary as a description for this document. The description must be under 1000 characters. Return only the description in your response.").response

            name = "query_engine_tool_" + name

            # replace characters that are not alphanumeric
            name = re.sub(r'\W+', '_', name)

            # if name is longer than 64 characters, truncate it
            if len(name) > 64:
                name = name[:64]

            # if description is longer than 1024 characters, truncate it
            if len(description) > 1024:
                description = description[:1024]

            print(f"Name: {name}")
            print(f"Description: {description}")

            tool = QueryEngineTool(
                query_engine=query_engine,
                metadata=ToolMetadata(
                    name=name,
                    description=description
                )
            )

            self._tools[file] = tool

            tools.append(tool)
        return tools
    

class AgentChat:
    def __init__(self, multi_document_rag: MultiDocumentRAG) -> None:
        logger.info("Initializing AgentChat")
        load_dotenv()
        self.llm_config = {"config_list": [{"model": 'gpt-4', "api_key": os.environ["OPENAI_API_KEY"]}]}
        self.message_queue = None
        self.rag = multi_document_rag

        # Create agents
        self.human_proxy = self._create_user_proxy_agent()
        self.query_analyzer = self._create_query_analyzer_agent()
        self.rag_agent = self._create_rag_agent()
        self.enhancement_agent = self._create_enhancement_agent()

    def _send_message(self, sender: str, content: str) -> None:
        """Helper method to send messages to the queue"""
        logger.info(f"Sending message from {sender}: {content}")
        if self.message_queue:
            self.message_queue.put({
                "sender": sender,
                "content": content
            })
        else:
            logger.warning("Message queue not set!")

    def _create_user_proxy_agent(self) -> ConversableAgent:
        """Creates the human proxy agent to represent the user in the chat"""
        user_proxy = UserProxyAgent(
            name="user_proxy",
            code_execution_config={"use_docker": False}
        )

        # No message handler needed

        return user_proxy


    def _create_query_analyzer_agent(self) -> ConversableAgent:
        """Creates the query analysis agent"""
        system_message = """You analyze car repair queries to ensure they contain all required information.
        Required information:
        1. Car brand and model
        2. Year of manufacture
        3. Specific part or system involved
        4. Nature of the problem or maintenance task

        If any information is missing, ask ONE question at a time to get it.
        If all information is present, create a SUMMARY in this format:

        SUMMARY:
        Vehicle: [Year] [Brand] [Model]
        Part/System: [Specific part]
        Task: [Detailed description of the problem/task]
        Additional Notes: [Any relevant details provided by user]

        Return ONLY the question if information is missing, or ONLY the SUMMARY if all information is present."""

        agent = ConversableAgent(
            name="query_analyzer",
            system_message=system_message,
            llm_config=self.llm_config
        )
        
        async def reply_func(
            recipient: ConversableAgent,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
        ) -> Tuple[bool, Union[str, Dict, None]]:
            logger.info(f"Query analyzer received message: {messages}")
            flag, response = await self.query_analyzer.a_generate_oai_reply(messages)
            logger.info(f"Query analyzer response: {response}")
            self._send_message("Query Analyzer", response)
            return flag, response

        agent.register_reply(
            trigger=lambda sender: True,
            reply_func=reply_func
        )
        
        return agent

    def _create_rag_agent(self) -> ConversableAgent:
        """Creates the RAG agent"""
        system_message = """You handle knowledge base queries for car repair information.
        When you receive a SUMMARY:
        1. Use the query_knowledge_base function with the SUMMARY
        2. Share the retrieved instructions

        Do NOT make up information or rely on general knowledge."""

        agent = ConversableAgent(
            name="rag_agent",
            system_message=system_message,
            llm_config=self.llm_config
        )

        def query_knowledge_base(query: str) -> str:
            logger.info(f"Querying knowledge base: {query}")
            try:
                response = self.rag.query(query).response
                logger.info(f"Knowledge base response: {response}")
                return response
            except Exception as e:
                logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
                return f"Error querying knowledge base: {str(e)}"

        # Register RAG function
        # agent.register_for_llm(description="Queries the car repair knowledge base")(query_knowledge_base)
        # agent.register_for_execution()(query_knowledge_base)

        async def reply_func(
            recipient: ConversableAgent,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
        ) -> Tuple[bool, Union[str, Dict, None]]:
            logger.info(f"RAG agent received message: {messages}")
            last_message = messages[-1].get("content")
            response = query_knowledge_base(last_message)
            logger.info(f"RAG agent response: {response}")
            self._send_message("RAG Agent", response)
            return True, response

        agent.register_reply(
            trigger=lambda sender: True,
            reply_func=reply_func
        )

        return agent

    def _create_enhancement_agent(self) -> ConversableAgent:
        """Creates the enhancement agent"""
        system_message = """You enhance repair instructions by:
        1. Identifying technical terms and jargon
        2. Adding clear explanations
        3. Formatting for readability

        Always structure your response as:

        REPAIR INSTRUCTIONS:
        [Enhanced instructions with better formatting]

        TECHNICAL TERMS EXPLAINED:
        - Term 1: Simple explanation
        - Term 2: Simple explanation with analogy

        SAFETY NOTES:
        [Any relevant safety information]"""

        agent = ConversableAgent(
            name="enhancement_agent",
            system_message=system_message,
            llm_config=self.llm_config
        )

        async def reply_func(
            recipient: ConversableAgent,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
        ) -> Tuple[bool, Union[str, Dict, None]]:
            logger.info(f"Enhancement agent received message: {messages}")
            flag, response = await self.enhancement_agent.a_generate_oai_reply(messages)
            logger.info(f"Enhancement agent response: {response}")
            self._send_message("Enhancement Agent", response)
            return flag, response

        agent.register_reply(
            trigger=lambda sender: True,
            reply_func=reply_func
        )

        return agent

    def _is_summary(self, message: str) -> bool:
        """Check if a message contains a complete SUMMARY block"""
        return message.strip().startswith("SUMMARY:") and all(
            field in message for field in ["Vehicle:", "Part/System:", "Task:"]
        )

    async def process_message(self, message: str) -> None:
        """Main method to process user messages"""
        logger.info("Processing message")
        
        # Step 1: Query Analysis
        query_analyzer_response = await self.human_proxy.a_initiate_chat(
            self.query_analyzer,
            message=message,
            clear_history=False,
            max_turns=1
        )
        
        logger.info(f"Query analyzer response: {query_analyzer_response}")
        query_analyzer_message = query_analyzer_response.summary

        # If response is a question (no SUMMARY found), end conversation
        if not self._is_summary(query_analyzer_message):
            return
            
        # Step 2: RAG Query
        rag_response = await self.human_proxy.a_initiate_chat(
            self.rag_agent,
            message=query_analyzer_message,
            max_turns=1
        )

        logger.info(f"RAG agent response: {rag_response}")
        rag_response_message = rag_response.summary
        
        # Step 3: Enhancement
        await self.human_proxy.a_initiate_chat(
            self.enhancement_agent,
            message=rag_response_message,
            max_turns=1
        )
        
        logger.info("Message processing complete")

    def set_message_queue(self, queue):
        """Set the message queue for this chat session"""
        logger.info("Setting message queue")
        self.message_queue = queue
