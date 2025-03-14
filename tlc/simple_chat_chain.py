import os
from copy import deepcopy
from typing import List
from jinja2 import Template
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from .langchain_logging import log_chat

def _read_api_key() -> str:
    """Read the Anthropic API key from .anthropic_key file."""
    # Try current directory first
    if os.path.exists(".anthropic_key"):
        with open(".anthropic_key", "r") as f:
            return f.read().strip()
    
    # Try user's home directory
    home_key_path = os.path.expanduser("~/.anthropic_key")
    if os.path.exists(home_key_path):
        with open(home_key_path, "r") as f:
            return f.read().strip()
    
    raise FileNotFoundError("Could not find .anthropic_key in current directory or home directory")

class SimpleChat:
    def __init__(self, system_prompt: str):
        """
        Initialize a SimpleChat instance with a system prompt.
        
        Args:
            system_prompt: The system prompt to use for all conversations
        """
        self.api_key = _read_api_key()
        self.llm = ChatAnthropic(
            model="claude-3-7-sonnet-latest",
            api_key=self.api_key,
        )
        self.history: List[BaseMessage] = [SystemMessage(content=system_prompt)]
    
    def call(self, prompt_template: str, **kwargs) -> str:
        """
        Format the prompt template with kwargs and get a response from the LLM.
        
        Args:
            prompt_template: A Jinja2 template string
            **kwargs: Arguments to format the template with
        
        Returns:
            The AI's response string
        """
        # Format the prompt using Jinja2
        template = Template(prompt_template)
        formatted_prompt = template.render(**kwargs)
        
        # Add the human message to history
        human_message = HumanMessage(content=formatted_prompt)
        self.history.append(human_message)
        
        try:
            # Get response from LLM
            response = self.llm.invoke(self.history)
            
            # Add AI response to history
            ai_message = AIMessage(content=response.content)
            self.history.append(ai_message)
            
            # Log the conversation
            log_chat(self.history)
            
            return response.content
            
        except Exception as e:
            # Remove the human message from history if we failed
            self.history.pop()
            raise e
    
    def clone(self) -> 'SimpleChat':
        """
        Create a copy of this chat instance with the same history.
        
        Returns:
            A new SimpleChat instance with copied history
        """
        new_chat = SimpleChat(self.history[0].content)  # Create new instance with same system prompt
        new_chat.history = deepcopy(self.history)  # Deep copy the history
        return new_chat 