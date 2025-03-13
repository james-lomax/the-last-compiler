from typing import List, Optional
import json
import os
import datetime
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage


@dataclass_json
@dataclass
class ChatLogBranch:
    messages: List[str] = field(default_factory=list)
    branches: List['ChatLogBranch'] = field(default_factory=list)


# Global variable to store all branches of conversations
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


def _find_branch_insertion_point(branch: ChatLogBranch, messages_str: List[str], index: int = 0) -> None:
    """
    Recursively find where to insert new messages in the branch structure.
    
    Args:
        branch: Current branch being examined
        messages_str: List of string messages to insert
        index: Current index in the branch's message list
    """
    # If we've gone through all messages in the current branch
    if index >= len(branch.messages):
        # If there are more messages to add
        if index < len(messages_str):
            # Check if any existing branch starts with the next message
            for sub_branch in branch.branches:
                if sub_branch.messages and sub_branch.messages[0] == messages_str[index]:
                    _find_branch_insertion_point(sub_branch, messages_str, 1)
                    return
            
            # No matching branch found, create a new one
            new_branch = ChatLogBranch(messages=messages_str[index:], branches=[])
            branch.branches.append(new_branch)
        return
    
    # If current message matches
    if index < len(messages_str) and branch.messages[index] == messages_str[index]:
        _find_branch_insertion_point(branch, messages_str, index + 1)
    else:
        # Split the branch at the divergence point
        new_branch1 = ChatLogBranch(
            messages=branch.messages[index:],
            branches=branch.branches
        )
        
        # Create a new branch for the new message chain
        new_branch2 = ChatLogBranch(
            messages=messages_str[index:],
            branches=[]
        )
        
        # Update the current branch
        branch.messages = branch.messages[:index]
        branch.branches = [new_branch1, new_branch2]


def log_chat(messages: List[BaseMessage]) -> None:
    """
    Log a conversation branch.
    
    Args:
        messages: List of BaseMessage objects representing a conversation
    """
    # Convert messages to strings
    messages_str = [_message_to_string(msg) for msg in messages]
    
    # If this is the first log, create the root branch
    if not log_branches:
        log_branches.append(ChatLogBranch(messages=messages_str, branches=[]))
        return
    
    # Find where to insert in the existing tree
    for branch in log_branches:
        if branch.messages and branch.messages[0] == messages_str[0]:
            _find_branch_insertion_point(branch, messages_str, 1)
            return
    
    # If no matching root branch, create a new one
    log_branches.append(ChatLogBranch(messages=messages_str, branches=[]))


def save_logs() -> None:
    """
    Save logs to a JSON file in slop/logs/session/<timestamp>.json
    """
    # Create directory if it doesn't exist
    log_dir = os.path.join("slop", "logs", "session")
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{timestamp}.json")
    
    # Save logs as JSON
    with open(log_file, "w") as f:
        json.dump([b.to_dict() for b in log_branches], f, indent=2) 