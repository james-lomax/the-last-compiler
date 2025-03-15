"""
Tests for the langchain_logging module.
"""

import os
import json
import shutil
import pytest
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from tlc.llm.langchain_logging import log_chat, save_logs, log_branches, ChatLogBranch


@pytest.fixture
def setup_teardown():
    """Setup and teardown for tests."""
    # Clear log_branches before each test
    log_branches.clear()
    
    # Create a temporary logs directory
    test_log_dir = os.path.join("slop", "logs", "session")
    os.makedirs(test_log_dir, exist_ok=True)
    
    yield
    
    # Clear log_branches after each test
    log_branches.clear()


def test_log_chat_single_branch(setup_teardown):
    """Test logging a single branch of conversation."""
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])

    assert log_branches == [
        ChatLogBranch(messages=["Human: Hello", "AI: Hello"], branches=[])
    ]


def test_log_chat_branching(setup_teardown):
    """Test logging a branching conversation."""
    # First branch
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])
    
    # Second branch with same human message but different AI response
    log_chat([HumanMessage(content="Hello"), AIMessage(content="What?")])

    assert len(log_branches) == 1
    assert log_branches[0].messages == ["Human: Hello"]
    assert len(log_branches[0].branches) == 2
    
    # Check the first branch
    assert log_branches[0].branches[0].messages == ["AI: Hello"]
    assert log_branches[0].branches[0].branches == []
    
    # Check the second branch
    assert log_branches[0].branches[1].messages == ["AI: What?"]
    assert log_branches[0].branches[1].branches == []


def test_log_chat_complex_branching(setup_teardown):
    """Test logging a more complex branching conversation."""
    # First conversation
    log_chat([
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
        HumanMessage(content="How are you?"),
        AIMessage(content="I'm good, thanks!")
    ])
    
    # Second conversation with branching at the second message
    log_chat([
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
        HumanMessage(content="What's your name?"),
        AIMessage(content="I'm an AI assistant.")
    ])
    
    # Third conversation with branching at the first message
    log_chat([
        HumanMessage(content="Hi"),
        AIMessage(content="Hello!"),
        HumanMessage(content="Can you help me?"),
        AIMessage(content="Of course!")
    ])
    
    # Verify the structure
    assert len(log_branches) == 2  # Two root branches: "Hello" and "Hi"
    
    # Check the first root branch (starting with "Hello")
    hello_branch = log_branches[0]
    assert hello_branch.messages == ["Human: Hello", "AI: Hi there!"]
    assert len(hello_branch.branches) == 2
    
    # Check the branches of the "Hello" conversation
    how_are_you_branch = hello_branch.branches[0]
    assert how_are_you_branch.messages == ["Human: How are you?", "AI: I'm good, thanks!"]
    
    whats_your_name_branch = hello_branch.branches[1]
    assert whats_your_name_branch.messages == ["Human: What's your name?", "AI: I'm an AI assistant."]
    
    # Check the second root branch (starting with "Hi")
    hi_branch = log_branches[1]
    assert hi_branch.messages == ["Human: Hi", "AI: Hello!", "Human: Can you help me?", "AI: Of course!"]


def test_save_logs(setup_teardown, monkeypatch):
    """Test saving logs to a file."""
    # Mock datetime to get a consistent filename
    class MockDatetime:
        @staticmethod
        def now():
            class MockNow:
                @staticmethod
                def strftime(format_str):
                    return "20230101_120000"
            return MockNow()
    
    monkeypatch.setattr("tlc.llm.langchain_logging.datetime.datetime", MockDatetime)
    
    # Add some logs
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hi there!")])
    
    # Check that the log file was created
    log_file = os.path.join("slop", "logs", "session", "20230101_120000.json")
    assert os.path.exists(log_file)
    
    # Check the contents of the log file
    with open(log_file, "r") as f:
        log_data = json.load(f)
    
    assert len(log_data) == 1
    assert log_data[0]["messages"] == ["Human: Hello", "AI: Hi there!"]
    assert log_data[0]["branches"] == []


def test_system_message(setup_teardown):
    """Test logging with system messages."""
    log_chat([
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!")
    ])

    assert log_branches == [
        ChatLogBranch(messages=[
            "System: You are a helpful assistant.",
            "Human: Hello",
            "AI: Hi there!"
        ], branches=[])
    ] 