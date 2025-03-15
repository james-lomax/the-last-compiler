"""
Provides a simple logging interface for langchain, recording branching conversations
so that we can clearly inspect what prompts were used and what the responses were.
"""

import os
import json
import datetime
from typing import List, Dict, Any
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from langchain.schema import BaseMessage, AIMessage, HumanMessage, SystemMessage


@dataclass_json
@dataclass
class ChatLogBranch:
    """Represents a branch in the conversation log tree."""
    messages: List[str]
    branches: List['ChatLogBranch']


# Global variable to store all branches of the conversation
log_branches: List[ChatLogBranch] = []


def _message_to_string(message: BaseMessage) -> str:
    """Convert a BaseMessage to a string representation."""
    if isinstance(message, AIMessage):
        return f"AI: {message.content}"
    elif isinstance(message, HumanMessage):
        return f"Human: {message.content}"
    elif isinstance(message, SystemMessage):
        return f"System: {message.content}"
    else:
        return f"{message.type}: {message.content}"


def _find_branch_insertion_point(messages: List[str]) -> None:
    """
    Find where to insert the new messages in the log_branches tree structure.
    Creates new branches as needed.
    """
    global log_branches
    
    if not messages:
        return
    
    # If log_branches is empty, create a new branch
    if not log_branches:
        log_branches.append(ChatLogBranch(messages=messages, branches=[]))
        return
    
    # Find the existing branch that matches the longest prefix of the new messages
    current_branches = log_branches
    current_messages = []
    
    for i, message in enumerate(messages):
        # Try to find a matching branch at the current level
        found_match = False
        
        for branch in current_branches:
            if i < len(branch.messages) and branch.messages[i] == message:
                # Found a matching message, continue with this branch
                current_messages.append(message)
                if i == len(messages) - 1:
                    # We've matched all messages, nothing to add
                    return
                
                if i + 1 < len(branch.messages):
                    # Continue matching in this branch
                    current_branches = [branch]
                else:
                    # Move to the next level of branches
                    current_branches = branch.branches
                
                found_match = True
                break
        
        if not found_match:
            # No match found, need to create a new branch
            remaining_messages = messages[i:]
            
            if not current_messages:
                # No common prefix, add a new root branch
                log_branches.append(ChatLogBranch(messages=remaining_messages, branches=[]))
            else:
                # Find the branch that contains the common prefix
                branch_to_modify = None
                search_branches = log_branches
                
                for j in range(len(current_messages)):
                    for branch in search_branches:
                        if j < len(branch.messages) and branch.messages[j] == current_messages[j]:
                            if j == len(current_messages) - 1:
                                branch_to_modify = branch
                                break
                            search_branches = branch.branches
                            break
                
                if branch_to_modify:
                    # Split the branch if needed
                    if len(branch_to_modify.messages) > len(current_messages):
                        # Create a new branch with the remaining messages from the existing branch
                        new_branch = ChatLogBranch(
                            messages=branch_to_modify.messages[len(current_messages):],
                            branches=branch_to_modify.branches
                        )
                        # Update the existing branch
                        branch_to_modify.messages = branch_to_modify.messages[:len(current_messages)]
                        branch_to_modify.branches = [new_branch]
                    
                    # Add the new branch
                    branch_to_modify.branches.append(
                        ChatLogBranch(messages=remaining_messages, branches=[])
                    )
            
            return


def log_chat(messages: List[BaseMessage]) -> None:
    """
    Log a chat conversation, maintaining a tree structure of all conversation branches.
    
    Args:
        messages: List of BaseMessage objects representing the conversation
    """
    # Convert messages to strings
    message_strings = [_message_to_string(msg) for msg in messages]
    
    # Insert into the log_branches tree structure
    _find_branch_insertion_point(message_strings)
    
    # Save logs after each update
    save_logs()


def save_logs() -> None:
    """
    Save the logs to a JSON file in the slop/logs/session directory.
    Creates the directory if it doesn't exist.
    """
    # Create the logs directory if it doesn't exist
    log_dir = os.path.join("slop", "logs", "session")
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate a timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{timestamp}.json")
    
    # Convert log_branches to a dictionary and save as JSON
    with open(log_file, "w") as f:
        json.dump([branch.to_dict() for branch in log_branches], f, indent=2) 