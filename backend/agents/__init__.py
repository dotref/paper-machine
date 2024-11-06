from typing import Type, Dict
from .base_agent import BaseAgent, AgentResponse
from .search_agent import SearchAgent
from .rag_agent import RAGAgent
from .query_agent import QueryAgent

# Registry of available agents
available_agents: Dict[str, Type[BaseAgent]] = {
    'search': SearchAgent,
    'rag': RAGAgent,
    'query': QueryAgent
}

def get_agent(agent_type: str, config: Dict = None) -> BaseAgent:
    """
    Factory function to create agent instances
    
    Args:
        agent_type: Type of agent to create
        config: Configuration for the agent
    
    Returns:
        An instance of the requested agent
    
    Raises:
        ValueError: If agent_type is not supported
    """
    if agent_type not in available_agents:
        raise ValueError(f"Unsupported agent type: {agent_type}. "
                        f"Available types: {list(available_agents.keys())}")
    
    return available_agents[agent_type](config)

__all__ = [
    'BaseAgent',
    'AgentResponse',
    'SearchAgent',
    'RAGAgent',
    'QueryAgent',
    'get_agent',
    'available_agents'
]