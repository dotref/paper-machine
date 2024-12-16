from typing import List, Dict, Optional, Tuple, Any, Callable, Union
import os
import re
from dotenv import load_dotenv
import logging
import asyncio
logger = logging.getLogger(__name__)

import pyprojroot
root_dir = pyprojroot.here()

from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader, Settings
from llama_index.core import load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.retrievers import QueryFusionRetriever

from autogen import ConversableAgent, UserProxyAgent, Agent, GroupChat, GroupChatManager


class MultiDocumentRetrieval():
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
        
        self._splitter = SentenceSplitter(chunk_size=256)
        self._indices = {}
        self._retriever = None
        self._retrievers = {}
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


    def setup_retriever(self, system_prompt: str = None) -> None:
        '''
        Setup the agent with tools from all documents.
        '''
        retrievers = self._get_tools()
        if not retrievers:
            self._retriever = None
            return

        self._retriever = QueryFusionRetriever(
            retrievers,
            similarity_top_k=5,
            num_queries=1,
            mode="reciprocal_rerank",
            use_async=True,
            verbose=True,
        )
    

    async def retrieve(self, query_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Query across all documents and return response with source information.
        Returns tuple of (response_text, source_chunks)
        """
        if not self._retriever:
            return []

        nodes_with_scores = await self._retriever.aretrieve(query_text)

        return nodes_with_scores


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
        
        reader = SimpleDirectoryReader(input_files=[os.path.join(self.upload_dir, file) for file in new_files])
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

            if file in self._retrievers:
                del self._retrievers[file]

            print(f"Deleted index for {file}")
        self._modified = True
    

    def _create_index(self, file: str, documents: str) -> VectorStoreIndex:
        '''
        Create index from documents.
        '''
        all_nodes = []
        for page_number, document in enumerate(documents):
            # get nodes from sentence splitter
            nodes = self._splitter.get_nodes_from_documents([document])
            for node in nodes:
                # add page number
                node.metadata['page_label'] = page_number
            all_nodes.extend(nodes)

        index = VectorStoreIndex(all_nodes, storage_context=self.storage_context)
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


    def _get_tools(self) -> list:
        '''
        Get tools from all indices
        '''
        retrievers = []
        for file, index in self._indices.items():
            if file in self._retrievers:
                retrievers.append(self._retrievers[file])
                continue

            retriever = index.as_retriever()
            self._retrievers[file] = retriever

            retrievers.append(retriever)
        return retrievers
    

class AgentChat:
    def __init__(self, knowledge_base: MultiDocumentRetrieval) -> None:
        logger.info("Initializing AgentChat")
        load_dotenv()
        self.llm_config = {"config_list": [{"model": 'gpt-4', "api_key": os.environ["OPENAI_API_KEY"]}]}
        self.message_queue = None
        self.knowledge_base = knowledge_base
        self._chat_history = []

        # Create Group Chat

        self.user_proxy_agent = self._create_user_proxy_agent()
        self.query_analyzer = self._create_query_analyzer_agent()
        self.rag_agent = self._create_rag_agent()
        self.enhancement_agent = self._create_enhancement_agent()

        self.group_chat = GroupChat(
            agents=[self.user_proxy_agent, self.query_analyzer, self.rag_agent, self.enhancement_agent],
            messages=[]
        )

        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config
        )


    async def _safe_generate_reply(self, agent, messages, max_retries=3, timeout=30, sources=[]):
        """Helper function to safely generate and send replies with timeout and error handling"""
        try:
            # Create task with timeout
            async with asyncio.timeout(timeout):
                flag, response = await agent.a_generate_oai_reply(messages)
                if not response:
                    return True, "ERROR: I encountered an error generating a response. Please try again."
                self._send_message(agent.name, response, sources)
                return flag, response
        except asyncio.TimeoutError:
            logger.error(f"Timeout error generating reply for {agent.name}")
            return True, "ERROR: I took too long to respond. Please try again."
        except Exception as e:
            logger.error(f"Error generating reply for {agent.name}: {str(e)}", exc_info=True)
            return True, f"ERROR: {str(e)}"


    def _send_message(self, sender: str, content: str, sources: list[dict] = []) -> None:
        """Helper method to send messages to the queue"""
        logger.info(f"Sending message from {sender}: {content}")
        logger.info(f"Sources length: {len(sources)}")

        name = ' '.join(word.capitalize() for word in sender.split('_'))

        # Remove any tag prefixes like "CLARIFICATION REQUEST: " from the content
        if ':' in content:
            tag, message = content.split(':', 1)
            if tag.isupper():  # Only remove if it looks like a tag (all caps)
                content = message

        if self.message_queue:
            self.message_queue.put({
                "sender": name,
                "content": content,
                "sources": sources
            })
        else:
            logger.warning("Message queue not set!")


    def _create_group_chat_manager(self) -> GroupChatManager:
        system_message = """You are a helpful group chat manager. 
Your job is to forward messages between agents based on the flow below.

user_proxy_agent:
- If the user_proxy_agent returns a QUESTION, you must pass it to the query_analyzer_agent.

query_analyzer_agent:
- If the query_analyzer_agent returns an ERROR, you must pass it to the user_proxy_agent.
- If the query_analyzer_agent returns a CLARIFICATION REQUEST, you must pass it to the user_proxy_agent.
- If the query_analyzer_agent returns a INFORMATION REQUEST, you must pass it to the enhancement_agent.
- If the query_analyzer_agent returns a INSTRUCTIONS REQUEST, you must pass it to the rag_agent.

rag_agent:
- If the rag_agent returns an ERROR, you must pass it to the user_proxy_agent.
- If the rag_agent returns REPAIR INSTRUCTIONS, you must pass it to the enhancement_agent.

enhancement_agent:
- If the enhancement_agent returns an ERROR, you must pass it to the user_proxy_agent.
- If the enhancement_agent returns an ADDITIONAL INFORMATION, you must pass it to the user_proxy_agent.
- If the enhancement_agent returns an INFORMATION EXPLAINED, you must pass it to the user_proxy_agent."""
        group_chat_manager = GroupChatManager(
            name="group_chat_manager",
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            system_message=system_message
        )
        return group_chat_manager


    def _create_user_proxy_agent(self) -> ConversableAgent:
        """Creates the human proxy agent to represent the user in the chat"""
        user_proxy_agent = UserProxyAgent(
            name="user_proxy_agent",
            human_input_mode="NEVER",
            code_execution_config={"use_docker": False},
            is_termination_msg=lambda message: True # Always True
        )
        return user_proxy_agent


    def _create_query_analyzer_agent(self) -> ConversableAgent:
        """Creates the query analysis agent"""
        system_message = """You are a helpful assistant trusted to analyze users’ car repair questions.
You must follow the below flow:

When you receive a QUESTION, you must determine whether the user is asking for information or repair instructions.
- If the user is asking for information, you must return an INFORMATION REQUEST using the format:
INFORMATION REQUEST: [User’s question]
- If the user is asking for repair instructions, you must first determine if you have all the information to construct an INSTRUCTIONS REQUEST.
    - If you have all the information, you must return an INSTRUCTIONS REQUEST using the format:
INSTRUCTIONS REQUEST:
- Part/System: [Specific part]
- Task: [Detailed description of the problem/task]
    - If you do not have all the information, you must return a CLARIFICATION REQUEST using the format:
CLARIFICATION REQUEST: 
[Request for missing information]

Return your response to the group_chat_manager only."""

        agent = ConversableAgent(
            name="query_analyzer_agent",
            system_message=system_message,
            llm_config=self.llm_config
        )
        
        async def reply_func(
            recipient: ConversableAgent,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
        ) -> Tuple[bool, Union[str, Dict, None]]:
            flag, response = await self._safe_generate_reply(self.query_analyzer, messages)
            return flag, response

        agent.register_reply(
            trigger=lambda sender: True,
            reply_func=reply_func
        )
        
        return agent


    def _create_rag_agent(self) -> ConversableAgent:
        """Creates the rag_agent"""
        system_message = """You handle knowledge base queries for car repair information.
When you receive a INSTRUCTIONS REQUEST, use the retrieved sources to generate repair instructions for the user's issue

Always structure your response as:

REPAIR INSTRUCTIONS:
[Clear and concise formatted instructions]

Do NOT make up information or rely on general knowledge.
Return your response to the group_chat_manager only."""

        agent = ConversableAgent(
            name="rag_agent",
            system_message=system_message,
            llm_config=self.llm_config
        )

        async def query_knowledge_base(query: str) -> list[NodeWithScore]:
            logger.info(f"Querying knowledge base: {query}")
            try:
                async with asyncio.timeout(30):
                    nodes_with_scores = await self.knowledge_base.retrieve(query)
                    return nodes_with_scores
            except asyncio.TimeoutError:
                logger.error("Timeout error during document retrieval")
                raise TimeoutError("Document retrieval took too long")
            except Exception as e:
                logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
                raise
                
        async def reply_func(
            recipient: ConversableAgent,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
        ) -> Tuple[bool, Union[str, Dict, None]]:
            last_message = messages[-1].get("content")
            
            try:
                nodes_with_scores = await query_knowledge_base(last_message)
            except Exception as e:
                error_msg = f"ERROR: {str(e)}"
                return True, error_msg
            
            results = "SOURCES:\n"
            sources = []
            for node_with_score in nodes_with_scores:
                # Document id and node.text
                results += f"Document: {node_with_score.node.node_id}\n"
                results += f"Relevance Score: {node_with_score.score:.4f}\n"
                results += f"Page: {node_with_score.node.metadata['page_label']}\n"
                results += f"Text: {node_with_score.node.text}\n"
                results += "-" * 40 + "\n"

                sources.append({
                    "file_name": node_with_score.node.metadata['file_name'],
                    "page_label": node_with_score.node.metadata['page_label'],
                    "text": node_with_score.node.text
                })

            messages[-1]["content"] += "\n" + results
            
            flag, response = await self._safe_generate_reply(self.rag_agent, messages, sources=sources)
            return flag, response

        agent.register_reply(
            trigger=lambda sender: True,
            reply_func=reply_func
        )

        return agent


    def _create_enhancement_agent(self) -> ConversableAgent:
        """Creates the enhancement_agent"""
        system_message = """You are a helpful assistant trusted to help users with technical questions related to car repair.

When you receive REPAIR INSTRUCTIONS, identify the technical terms and return an ADDITIONAL INFORMATION using the format:
ADDITIONAL INFORMATION:
TECHNICAL TERMS EXPLAINED:
    - Term 1: Simple explanation
    - Term 2: Simple explanation with analogy
TOOLS CHECKLIST:
[List of tools needed to complete the repair, if any]
SAFETY PRECAUTIONS:
[Safety precautions to take, if any]
        
When you receive an INFORMATION REQUEST, return an INFORMATION EXPLAINED using the format:
INFORMATION EXPLAINED:
- [User's question]
- [Explanation of the information]
        
Return your response to the group_chat_manager only."""

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
            flag, response = await self._safe_generate_reply(self.enhancement_agent, messages)
            return flag, response

        agent.register_reply(
            trigger=lambda sender: True,
            reply_func=reply_func
        )

        return agent

    def _is_summary(self, message: str) -> bool:
        """Check if a message contains a complete SUMMARY block"""
        return message.strip().startswith("SUMMARY:") and all(
            field in message for field in ["Part/System:", "Task:"]
        )

    async def process_message(self, message: str) -> None:
        """Main method to process user messages"""
        logger.info("Processing message")

        # if no documents, return early
        if not self.knowledge_base._retriever:
            self._send_message("System", "No documents found. Please upload documents first.")
            return

        try:
            # resume group chat
            if self._chat_history:
                self.group_chat_manager.resume(self._chat_history)

            question = "QUESTION: " + message

            await self.user_proxy_agent.a_initiate_chat(recipient=self.group_chat_manager, message=question, clear_history=False)

            logger.info("Message processing complete")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            self._send_message("System", f"An unexpected error occurred: {str(e)}")

    def set_message_queue(self, queue):
        """Set the message queue for this chat session"""
        logger.info("Setting message queue")
        self.message_queue = queue