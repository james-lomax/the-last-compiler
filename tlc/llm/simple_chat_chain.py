import os
from typing import List, Dict, Any
import jinja2
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

from tlc.llm.langchain_logging import log_chat, save_logs

# Setup SQLite cache for langchain
set_llm_cache(SQLiteCache(database_path=".langchain.db"))

class SimpleChat:
    def __init__(self, system_prompt: str, debug_name: str | None = None, model: str = "claude-sonnet"):
        """
        Initialize a SimpleChat instance.
        
        Args:
            system_prompt: The system prompt to use for the chat
            model: The model to use, either "claude-sonnet" or "claude-haiku"
        """
        self.system_prompt = system_prompt
        self.history = [SystemMessage(content=system_prompt)]
        self.debug_name = debug_name
        # Determine the model name based on the input
        if model == "claude-sonnet":
            model_name = "claude-3-7-sonnet-latest"
        elif model == "claude-haiku":
            model_name = "claude-3-5-haiku-latest"
        else:
            raise ValueError(f"Unknown model: {model}. Use 'claude-sonnet' or 'claude-haiku'")
        
        # Get API key from .anthropic_key file
        api_key = self._get_api_key()
        
        # Initialize the model
        self.model = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            max_tokens=64_000,
        )
    
    def _get_api_key(self) -> str:
        """
        Get the Anthropic API key from the .anthropic_key file.
        
        Returns:
            The API key as a string
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
        
        raise FileNotFoundError("Could not find .anthropic_key file in current directory or home directory")
    
    def call(self, prompt_template: str, **kwargs) -> str:
        """
        Format the prompt template using Jinja2 with the input arguments,
        append it to the chat history, and get a response from the model.
        
        Args:
            prompt_template: A Jinja2 template string
            **kwargs: Arguments to pass to the template
            
        Returns:
            The model's response as a string
        """
        # Format the prompt using Jinja2
        template = jinja2.Template(prompt_template)
        formatted_prompt = template.render(**kwargs)
        
        # Append the formatted prompt to the chat history
        self.history.append(HumanMessage(content=formatted_prompt))
        
        # Get response from the model with streaming to handle large responses
        stream = self.model.stream(self.history)
        full_response = ""
        
        # Get the first chunk
        try:
            chunk = next(stream)
            full_response = chunk.content
            
            # Get the rest of the chunks
            for chunk in stream:
                full_response += chunk.content
        except StopIteration:
            pass  # Handle empty response
        
        # Append the response to the chat history
        self.history.append(AIMessage(content=full_response))
        
        # Log the chat history
        log_chat(self.history)

        if self.debug_name:
            with open(f"logs/{self.debug_name}.{len(self.history)}.md", "a") as f:
                f.writelines([_message_to_md(msg) for msg in self.history])
        
        return full_response
    
    def clone(self, debug_name: str | None = None) -> 'SimpleChat':
        """
        Create a copy of this SimpleChat instance with the same history.
        
        Returns:
            A new SimpleChat instance with the same history
        """
        # Create a new instance with the same system prompt and model
        new_chat = SimpleChat(
            self.system_prompt, 
            debug_name,
            self.model
        )
        
        # Copy the history
        new_chat.history = self.history.copy()
        
        return new_chat 
    
def _message_to_md(message: BaseMessage) -> str:
    """Convert a BaseMessage to a string representation."""
    if isinstance(message, AIMessage):
        return f"\n# AI\n\n{message.content}"
    elif isinstance(message, HumanMessage):
        return f"\n# Human\n\n{message.content}"
    elif isinstance(message, SystemMessage):
        return f"\n# System\n\n{message.content}"
    else:
        return f"\n# {message.type}\n\n{message.content}"
