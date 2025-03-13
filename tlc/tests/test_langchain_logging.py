import pytest
import os
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from tlc.langchain_logging import log_chat, log_branches, ChatLogBranch, save_logs


def test_log_chat_simple():
    # Reset log_branches for testing
    log_branches.clear()
    
    # Test with a simple conversation
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])

    assert len(log_branches) == 1
    assert log_branches[0].messages == ["Human: Hello", "AI: Hello"]
    assert log_branches[0].branches == []


def test_log_chat_branching():
    # Reset log_branches for testing
    log_branches.clear()
    
    # First conversation
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])
    
    # Second conversation with different AI response
    log_chat([HumanMessage(content="Hello"), AIMessage(content="What?")])
    
    assert len(log_branches) == 1
    assert log_branches[0].messages == ["Human: Hello"]
    assert len(log_branches[0].branches) == 2
    
    # Check first branch
    branch1 = log_branches[0].branches[0]
    assert branch1.messages == ["AI: Hello"]
    assert branch1.branches == []
    
    # Check second branch
    branch2 = log_branches[0].branches[1]
    assert branch2.messages == ["AI: What?"]
    assert branch2.branches == []


def test_log_chat_complex_branching():
    # Reset log_branches for testing
    log_branches.clear()
    
    # First conversation
    log_chat([
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
        HumanMessage(content="How are you?"),
        AIMessage(content="I'm good, thanks!")
    ])
    
    # Second conversation with same start but different continuation
    log_chat([
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
        HumanMessage(content="What's the weather like?"),
        AIMessage(content="I don't have real-time weather data.")
    ])
    
    # Third conversation with completely different start
    log_chat([
        HumanMessage(content="Good morning"),
        AIMessage(content="Good morning to you too!")
    ])
    
    # Check we have two root branches
    assert len(log_branches) == 2
    
    # Check first root branch (Hello)
    hello_branch = next(b for b in log_branches if b.messages[0] == "Human: Hello")
    assert hello_branch.messages == ["Human: Hello", "AI: Hi there!"]
    assert len(hello_branch.branches) == 2
    
    # Check the two sub-branches of the Hello branch
    how_are_you_branch = hello_branch.branches[0]
    assert how_are_you_branch.messages == ["Human: How are you?", "AI: I'm good, thanks!"]
    
    weather_branch = hello_branch.branches[1]
    assert weather_branch.messages == ["Human: What's the weather like?", "AI: I don't have real-time weather data."]
    
    # Check second root branch (Good morning)
    morning_branch = next(b for b in log_branches if b.messages[0] == "Human: Good morning")
    assert morning_branch.messages == ["Human: Good morning", "AI: Good morning to you too!"]
    assert morning_branch.branches == []


def test_different_message_types():
    # Reset log_branches for testing
    log_branches.clear()
    
    # Test with different message types
    log_chat([
        SystemMessage(content="You are a helpful assistant"),
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!")
    ])
    
    assert log_branches[0].messages == [
        "System: You are a helpful assistant",
        "Human: Hello",
        "AI: Hi there!"
    ]


def test_save_logs(tmp_path, monkeypatch):
    # Reset log_branches for testing
    log_branches.clear()
    
    # Create a test log
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hi there!")])
    
    # Create a temporary directory for logs
    test_log_dir = os.path.join(tmp_path, "logs", "session")
    os.makedirs(test_log_dir, exist_ok=True)
    
    # Patch the os.path.join function to use our test directory
    original_join = os.path.join
    
    def mock_join(*args):
        if args[0] == "slop" and args[1] == "logs" and args[2] == "session":
            return test_log_dir
        return original_join(*args)
    
    monkeypatch.setattr(os.path, "join", mock_join)
    
    # Mock datetime to get a predictable filename
    class MockDateTime:
        @staticmethod
        def now():
            class MockNow:
                @staticmethod
                def strftime(format_str):
                    return "20230101_120000"
            return MockNow()
    
    monkeypatch.setattr("datetime.datetime", MockDateTime)
    
    # Call save_logs
    save_logs()
    
    # Check that the file was created
    expected_file = os.path.join(test_log_dir, "20230101_120000.json")
    assert os.path.exists(expected_file)
    
    # Check the content of the file
    with open(expected_file, "r") as f:
        data = json.load(f)
        assert len(data) == 1
        assert "Human: Hello" in data[0]["messages"]
        assert "AI: Hi there!" in data[0]["messages"] 