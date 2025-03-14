import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .simple_chat_chain import SimpleChat

@pytest.fixture
def mock_anthropic():
    with patch('tlc.simple_chat_chain.ChatAnthropic') as mock:
        # Create a mock response object
        mock_response = Mock()
        mock_response.content = "Test response"
        
        # Configure the mock LLM
        mock_instance = mock.return_value
        mock_instance.invoke.return_value = mock_response
        
        yield mock_instance

@pytest.fixture
def mock_api_key():
    with patch('tlc.simple_chat_chain.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "test-api-key"
        with patch('tlc.simple_chat_chain.os.path.exists', return_value=True):
            yield

def test_init(mock_api_key, mock_anthropic):
    system_prompt = "You are a helpful assistant."
    chat = SimpleChat(system_prompt)
    
    assert len(chat.history) == 1
    assert isinstance(chat.history[0], SystemMessage)
    assert chat.history[0].content == system_prompt

def test_call_template_formatting(mock_api_key, mock_anthropic):
    chat = SimpleChat("System prompt")
    
    template = "Hello {{ name }}, {{ question }}"
    response = chat.call(template, name="Alice", question="how are you?")
    
    # Check that the LLM was called with correctly formatted prompt
    assert len(chat.history) == 3  # System + Human + AI
    assert isinstance(chat.history[1], HumanMessage)
    assert chat.history[1].content == "Hello Alice, how are you?"
    assert isinstance(chat.history[2], AIMessage)
    assert chat.history[2].content == "Test response"
    assert response == "Test response"

def test_clone(mock_api_key, mock_anthropic):
    original = SimpleChat("System prompt")
    original.call("Hello")  # Add some history
    
    clone = original.clone()
    
    # Check that histories match but are different objects
    assert len(clone.history) == len(original.history)
    assert clone.history != original.history  # Different objects
    for orig_msg, clone_msg in zip(original.history, clone.history):
        assert orig_msg.content == clone_msg.content
        assert isinstance(clone_msg, type(orig_msg))

def test_error_handling(mock_api_key, mock_anthropic):
    chat = SimpleChat("System prompt")
    mock_anthropic.invoke.side_effect = Exception("API Error")
    
    with pytest.raises(Exception):
        chat.call("Hello")
    
    # Check that failed message was removed from history
    assert len(chat.history) == 1  # Only system message remains
    assert isinstance(chat.history[0], SystemMessage) 