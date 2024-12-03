from typing import Dict, List, Optional
import os
from dataclasses import dataclass
from autogen import ConversableAgent
from dotenv import load_dotenv

def query_knowledge_base(query: str) -> str:
        """Function to query the RAG system"""
        # try:
        #     response = self.rag_system.query(query)
        #     return response
        # except Exception as e:
        #     return f"Error querying knowledge base: {str(e)}"
        return "Hello world\n" + query


class CarDIYRAGAgent:
    def __init__(self, rag_system):
        load_dotenv()
        self.llm_config = {
            "config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]
        }
        self.rag_system = rag_system
        
        # Create the RAG agent
        self.rag_agent = ConversableAgent(
            "rag_agent",
            system_message=self._get_rag_agent_prompt(),
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )

        # Create entry point agent
        self.entry_point = ConversableAgent(
            "entry_point",
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )

        # Register the RAG query function
        
        self.entry_point.register_for_llm(
            description="Queries the car repair knowledge base using the enriched query"
        )(query_knowledge_base)
        self.entry_point.register_for_execution()(query_knowledge_base)

        self.rag_agent.register_for_llm(
            description="Queries the car repair knowledge base using the enriched query"
        )(query_knowledge_base)

    def _get_rag_agent_prompt(self, query:str) -> str:
        return """The user has requested reviews for a restaurant. The inquired restaurant can be found in: '{restaurant_query}'. "
        f"Please suggest a function call to fetch the reviews for this restaurant, using the function 'fetch_restaurant_data'."
        3. Return relevant repair instructions and safety information
        
        Always use the query_car_knowledge function to get information.
        Never make up information or rely on general knowledge.
        """


    def get_repair_info(self, enriched_query: str) -> str:
        """Get repair information using the enriched query"""
        chat_result = self.entry_point.initiate_chat(
            self.rag_agent,
            message=f"Please provide repair instructions for this query:\n\n{enriched_query}",
            max_turns=2,
            summary_method="last_msg"
        )
        return chat_result

    def extract_response(self, chat_result) -> str:
        """Extract the actual response from the chat result"""
        # Get the last message which should be the RAG response
        if hasattr(chat_result, "messages") and chat_result.messages:
            return chat_result.messages[-1]["content"]
        return "No response found in chat result"
    

# Example usage
if __name__ == "__main__":
    from agentic_rag_2 import MultiDocumentRAG, root_dir
    
    # Initialize RAG system
    
    # UPLOAD_DIR = os.path.join(root_dir, "backend/uploads")
    # PERSIST_DIR = os.path.join(root_dir, "backend/storage")

    # rag = MultiDocumentRAG(UPLOAD_DIR, PERSIST_DIR)

    # rag.setup_indicies()

    # files = os.listdir(UPLOAD_DIR)
    # rag.create_indices(files)
    # rag.setup_agent()
    # rag_system = rag
    
    # Initialize the CarDIY system
    car_diy_system = CarDIYRAGAgent(None)
    
    # Process a query - this will start a conversation with the user
    result = car_diy_system.get_repair_info("The user's brake pad on their 2024 Tesla Model 3 is not working properly, causing the car to not stop effectively.")
    print("\nFinal Enhanced Response:")
    print(result)