import pytest
from langchain_core.messages import HumanMessage, AIMessage
from .langchain_logging import log_chat, log_branches, ChatLogBranch

def test_log_chat_basic():
    # Clear any existing logs
    log_branches.clear()
    
    # Test basic conversation
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])
    
    assert len(log_branches) == 1
    assert log_branches[0] == ChatLogBranch(
        messages=["Human: Hello", "AI: Hello"],
        branches=[]
    )

def test_log_chat_branching():
    # Clear any existing logs
    log_branches.clear()
    
    # First conversation
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])
    
    # Second conversation with different AI response
    log_chat([HumanMessage(content="Hello"), AIMessage(content="What?")])
    
    assert len(log_branches) == 1
    root = log_branches[0]
    assert root.messages == ["Human: Hello"]
    assert len(root.branches) == 2
    
    # Check both branches exist
    branch_messages = [branch.messages for branch in root.branches]
    assert ["AI: Hello"] in branch_messages
    assert ["AI: What?"] in branch_messages

def test_log_chat_complex_branching():
    # Clear any existing logs
    log_branches.clear()
    
    # First conversation
    log_chat([
        HumanMessage(content="Hello"),
        AIMessage(content="Hi"),
        HumanMessage(content="How are you?"),
        AIMessage(content="Good!")
    ])
    
    # Second conversation that branches at the second human message
    log_chat([
        HumanMessage(content="Hello"),
        AIMessage(content="Hi"),
        HumanMessage(content="What's the weather?"),
        AIMessage(content="Sunny!")
    ])
    
    assert len(log_branches) == 1
    root = log_branches[0]
    
    # Check the common prefix
    assert root.messages == ["Human: Hello", "AI: Hi"]
    assert len(root.branches) == 2
    
    # Check both conversation branches
    branch_messages = [branch.messages for branch in root.branches]
    assert ["Human: How are you?", "AI: Good!"] in branch_messages
    assert ["Human: What's the weather?", "AI: Sunny!"] in branch_messages 