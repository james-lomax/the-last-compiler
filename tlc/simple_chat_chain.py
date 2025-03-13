import os
import copy
import jinja2
from typing import Dict, Any, List, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class SimpleChat:
    """
    A simple chat interface for interacting with Anthropic's Claude model.
    Maintains conversation history and allows for forking conversations.
    """
    
    def __init__(self, system_prompt: str):
        """
        Initialize a new chat session with a system prompt.
        
        Args:
            system_prompt: The system prompt that sets the context for the conversation
        """
        # Read API key from .anthropic_key file
        api_key_path = os.path.expanduser("~/.anthropic_key")
        if not os.path.exists(api_key_path):
            api_key_path = ".anthropic_key"  # Try current directory
        
        with open(api_key_path, "r") as f:
            api_key = f.read().strip()
        
        # Initialize the ChatAnthropic client
        self.client = ChatAnthropic(
            model="claude-3-7-sonnet-latest",
            api_key=api_key,
        )
        
        # Initialize conversation history with system prompt
        self.history = [SystemMessage(content=system_prompt)]
        
        # Store the system prompt for cloning
        self.system_prompt = system_prompt
        
        # Initialize Jinja2 environment for template rendering
        self.jinja_env = jinja2.Environment()
    
    def call(self, prompt_template: str, input: Dict[str, Any]) -> str:
        """
        Render the prompt template with the input, send it to the model,
        and update the conversation history.
        
        Args:
            prompt_template: A Jinja2 template string for the prompt
            input: A dictionary of variables to render the template with
            
        Returns:
            The model's response as a string
        """
        # Render the prompt template with the input
        template = self.jinja_env.from_string(prompt_template)
        rendered_prompt = template.render(**input)
        
        # Add the user message to history
        self.history.append(HumanMessage(content=rendered_prompt))
        
        # Call the model with the conversation history
        response = self.client.invoke(self.history)
        
        # Add the model's response to history
        ai_message = AIMessage(content=response.content)
        self.history.append(ai_message)
        
        return response.content
    
    def clone(self) -> 'SimpleChat':
        """
        Create a copy of this chat session with the same history.
        This allows forking the conversation to explore different paths.
        
        Returns:
            A new SimpleChat instance with the same history
        """
        new_chat = SimpleChat(self.system_prompt)
        new_chat.history = copy.deepcopy(self.history)
        return new_chat 