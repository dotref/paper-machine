from typing import Dict, List, Optional
import os
from dataclasses import dataclass
from autogen import ConversableAgent
from dotenv import load_dotenv

def get_response_enhancement_prompt() -> str:
    return """You are an expert at explaining technical car terminology.
    
    Your task is to:
    1. Identify technical terms in the provided DIY instructions
    2. Add explanations while maintaining the original instructions
    3. Format the response as follows:

    [Original instructions with technical terms highlighted]

    Technical Terms Explained:
    - [Term 1]: [Simple explanation with everyday examples]
    - [Term 2]: [Simple explanation with everyday examples]
    
    Keep the original instructions intact but make them more accessible to DIY beginners."""


class CarDIYResponseEnhancementAgent:
    def __init__(self):
        load_dotenv()
        self.llm_config = {
            "config_list": [{"model": os.environ["OPENAI_MODEL"], "api_key": os.environ["OPENAI_API_KEY"]}]
        }
        
        # Create the response enhancement agent
        self.agent = ConversableAgent(
            "response_enhancement_agent",
            system_message=get_response_enhancement_prompt(),
            llm_config=self.llm_config,
            human_input_mode="NEVER"  # No need for human input in enhancement phase
        )

        self.entry_point = ConversableAgent(
            "entry_point",
            llm_config=False,  # no LLM used for entry point
            human_input_mode="NEVER"
        )

    def enhance_response(self, response: str) -> str:
        enhanced_response = self.entry_point.initiate_chat(
            self.agent,
            message=f"Please enhance this DIY instruction with technical term explanations:\n\n{response}",
            max_turns = 1,
        )
        return enhanced_response
    
if __name__ == "__main__":
    # Test response enhancement
    enhancement_agent = CarDIYResponseEnhancementAgent()
    sample_response = """
    1. Remove the caliper bolts using a 13mm socket
    2. Compress the brake piston using a c-clamp
    3. Replace the brake pads and ensure proper fitment
    """
    enhanced = enhancement_agent.enhance_response(sample_response)
    print("\nEnhanced Response:", enhanced)