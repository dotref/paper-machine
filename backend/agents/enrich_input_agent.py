from typing import Dict, List, Optional
import os
from dataclasses import dataclass
from autogen import ConversableAgent
from dotenv import load_dotenv

def get_query_enrichment_prompt() -> str:
    return """You are a car expert who helps gather detailed information about DIY car repair queries.
    
    Your task is to have a conversation with the user to gather missing information about:
    1. Car brand and model
    2. Year of manufacture
    3. Specific part or system involved
    4. Nature of the problem or maintenance task

    Guidelines:
    - Ask ONE question at a time
    - If any information is already provided in the query, don't ask for it again
    - Wait for user's response before asking the next question
    - Once all information is gathered, provide a summary in this format:
    
    SUMMARY:
    Vehicle: [Year] [Brand] [Model]
    Part/System: [Specific part]
    Task: [Detailed description of the problem/task]
    Additional Notes: [Any relevant details provided by user]
    """


class CarDIYQueryEnrichmentAgent:
    def __init__(self):
        load_dotenv()
        self.llm_config = {
            "config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]
        }
        
        # Create the query enrichment agent
        self.query_enrich_agent = ConversableAgent(
            "query_enrich_agent",
            system_message=get_query_enrichment_prompt(),
            llm_config=self.llm_config,
            human_input_mode="NEVER",  # Enable direct interaction with user
            is_termination_msg=self._is_termination_msg
        )

        self.human_proxy = ConversableAgent(
            "human_proxy",
            llm_config=False,  # no LLM used for human proxy
            human_input_mode="ALWAYS",  # always ask for human input
            is_termination_msg=self._is_termination_msg
        )

    def _is_termination_msg(self, msg: Dict) -> bool:
        return "SUMMARY" in msg["content"]
    
    def initial_chat(self) -> Dict:
        # Start the conversation
        chat_result = self.query_enrich_agent.initiate_chat(
            self.human_proxy,
            message="How may I help you?",
            summary_method="reflection_with_llm",
            max_turns=5
        )
        
        return chat_result


# Example usage to test the agents independently
if __name__ == "__main__":
    # Test query enrichment
    enrichment_agent = CarDIYQueryEnrichmentAgent()
    enrichment_result = enrichment_agent.initial_chat()
    print("Enrichment Result:", enrichment_result.summary) # The summary will be used by RAG
    
    