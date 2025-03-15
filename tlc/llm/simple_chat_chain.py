"""
Simple chat interface for interacting with LLMs in a conversational manner.
Provides a clean API for chat-style interactions with Anthropic Claude models.
"""

import os
from typing import List, Optional
import jinja2
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_anthropic import ChatAnthropic
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from tlc.llm.langchain_logging import log_chat

# Setup SQLite cache for LLM responses
set_llm_cache(SQLiteCache(database_path=".langchain.db"))


def _get_anthropic_api_key() -> str:
    """
    Get the Anthropic API key from the .anthropic_key file.
    Looks in the current directory first, then in the user's home directory.
    """
    # Try to read from current directory
    if os.path.exists(".anthropic_key"):
        with open(".anthropic_key", "r") as f:
            return f.read().strip()
    
    # Try to read from home directory
    home_key_path = os.path.join(os.path.expanduser("~"), ".anthropic_key")
    if os.path.exists(home_key_path):
        with open(home_key_path, "r") as f:
            return f.read().strip()
    
    raise FileNotFoundError(
        "Anthropic API key not found. Please create a .anthropic_key file in the current "
        "directory or in your home directory with your Anthropic API key."
    )


class SimpleChat:
    """
    A simple chat interface for interacting with LLMs in a conversational manner.
    
    Maintains chat history and provides a clean API for chat-style interactions.
    """
    
    def __init__(self, system_prompt: str, model: str = "claude-sonnet"):
        """
        Initialize a new chat session.
        
        Args:
            system_prompt: The system prompt to use for the chat session
            model: The model to use, either "claude-sonnet" or "claude-haiku"
        """
        self.system_prompt = system_prompt
        self.history: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        
        # Map model name to actual model identifier
        model_mapping = {
            "claude-sonnet": "claude-3-7-sonnet-latest",
            "claude-haiku": "claude-3-5-haiku-latest"
        }
        
        if model not in model_mapping:
            raise ValueError(f"Unknown model: {model}. Available models: {', '.join(model_mapping.keys())}")
        
        # Get API key and initialize the chat model
        api_key = _get_anthropic_api_key()
        self.llm = ChatAnthropic(
            model=model_mapping[model],
            api_key=api_key,
        )
    
    def call(self, prompt_template: str, **kwargs) -> str:
        """
        Format the prompt template with the provided arguments and get a response from the LLM.
        
        Args:
            prompt_template: A Jinja2 template string for the prompt
            **kwargs: Arguments to format the prompt template with
            
        Returns:
            The response from the LLM
        """
        # Format the prompt template using Jinja2
        environment = jinja2.Environment()
        template = environment.from_string(prompt_template)
        formatted_prompt = template.render(**kwargs)
        
        # Add the formatted prompt to the chat history
        self.history.append(HumanMessage(content=formatted_prompt))
        
        # Get a response from the LLM
        response = self.llm.invoke(self.history)
        
        # Add the response to the chat history
        self.history.append(AIMessage(content=response.content))
        
        # Log the chat history
        log_chat(self.history)
        
        return response.content
    
    def clone(self) -> 'SimpleChat':
        """
        Create a copy of this chat session with the same history.
        
        Returns:
            A new SimpleChat instance with the same history
        """
        new_chat = SimpleChat(self.system_prompt)
        new_chat.history = self.history.copy()
        new_chat.llm = self.llm
        return new_chat 