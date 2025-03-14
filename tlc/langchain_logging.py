from dataclasses import dataclass
from typing import List
from dataclasses_json import dataclass_json
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
import json
import os
from datetime import datetime

@dataclass_json
@dataclass
class ChatLogBranch:
    messages: List[str]
    branches: List['ChatLogBranch']

# Global variable to store all branches
log_branches: List[ChatLogBranch] = []

def _message_to_string(message: BaseMessage) -> str:
    """Convert a BaseMessage to a string representation."""
    if isinstance(message, AIMessage):
        prefix = "AI: "
    elif isinstance(message, HumanMessage):
        prefix = "Human: "
    elif isinstance(message, SystemMessage):
        prefix = "System: "
    else:
        prefix = f"{message.__class__.__name__}: "
    
    return prefix + message.content

def _find_or_create_branch(current_messages: List[str], current_branch: ChatLogBranch) -> None:
    """
    Recursively find where to insert new messages in the tree structure,
    creating new branches as needed.
    """
    if not current_messages:
        return
    
    # Check if this message exists in any branch
    matching_branch = None
    for branch in current_branch.branches:
        if branch.messages and branch.messages[0] == current_messages[0]:
            matching_branch = branch
            break
    
    if matching_branch:
        # Continue down this branch
        _find_or_create_branch(current_messages[1:], matching_branch)
    else:
        # Create new branch
        new_branch = ChatLogBranch(messages=current_messages, branches=[])
        current_branch.branches.append(new_branch)

def log_chat(messages: List[BaseMessage]) -> None:
    """
    Log a chat conversation, maintaining a tree structure of all conversation branches.
    """
    # Convert messages to strings
    str_messages = [_message_to_string(msg) for msg in messages]
    
    # If this is the first conversation
    if not log_branches:
        log_branches.append(ChatLogBranch(messages=str_messages, branches=[]))
        save_logs()
        return
    
    # Find the first message that differs from existing branches
    root = log_branches[0]
    common_prefix_length = 0
    for i, msg in enumerate(str_messages):
        if i >= len(root.messages) or msg != root.messages[i]:
            break
        common_prefix_length += 1
    
    if common_prefix_length == 0:
        # Completely new conversation
        log_branches.append(ChatLogBranch(messages=str_messages, branches=[]))
    elif common_prefix_length < len(str_messages):
        # Create a new branch from the point of divergence
        if common_prefix_length < len(root.messages):
            # Split the existing conversation into a branch
            old_messages = root.messages[common_prefix_length:]
            old_branches = root.branches
            root.messages = root.messages[:common_prefix_length]
            root.branches = [ChatLogBranch(messages=old_messages, branches=old_branches)]
        
        # Add the new branch
        _find_or_create_branch(str_messages[common_prefix_length:], root)
    
    save_logs()

def save_logs() -> None:
    """
    Save the current logs to a JSON file in slop/logs/session/<timestamp>.json
    """
    log_dir = os.path.join("slop", "logs", "session")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{timestamp}.json")
    
    with open(log_file, 'w') as f:
        json.dump(log_branches, f, indent=2, default=lambda x: x.to_dict()) 