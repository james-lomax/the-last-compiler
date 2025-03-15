"""
Tests for the SimpleChat class.
"""

import unittest
from unittest.mock import patch, MagicMock
from tlc.llm.simple_chat_chain import SimpleChat


class TestSimpleChat(unittest.TestCase):
    """Test cases for the SimpleChat class."""

    @patch('tlc.llm.simple_chat_chain._get_anthropic_api_key')
    @patch('tlc.llm.simple_chat_chain.ChatAnthropic')
    @patch('tlc.llm.simple_chat_chain.log_chat')
    def test_chat_initialization(self, mock_log_chat, mock_chat_anthropic, mock_get_api_key):
        """Test that SimpleChat initializes correctly."""
        mock_get_api_key.return_value = "fake-api-key"
        mock_chat_instance = MagicMock()
        mock_chat_anthropic.return_value = mock_chat_instance

        # Initialize with default model (claude-sonnet)
        chat = SimpleChat("Test system prompt")
        
        # Check that the API key was retrieved
        mock_get_api_key.assert_called_once()
        
        # Check that ChatAnthropic was initialized with the correct model
        mock_chat_anthropic.assert_called_once_with(
            model="claude-3-7-sonnet-latest",
            api_key="fake-api-key"
        )

    @patch('tlc.llm.simple_chat_chain._get_anthropic_api_key')
    @patch('tlc.llm.simple_chat_chain.ChatAnthropic')
    @patch('tlc.llm.simple_chat_chain.log_chat')
    def test_chat_call(self, mock_log_chat, mock_chat_anthropic, mock_get_api_key):
        """Test that SimpleChat.call works correctly."""
        mock_get_api_key.return_value = "fake-api-key"
        mock_chat_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is Paris, the capital of France."
        mock_chat_instance.invoke.return_value = mock_response
        mock_chat_anthropic.return_value = mock_chat_instance

        # Initialize chat
        chat = SimpleChat("You are a helpful assistant.")
        
        # Call with template and variables
        response = chat.call(
            "Hello, my name is {{ name }}. {{ question }}",
            name="Alice",
            question="What's the capital of France?"
        )
        
        # Check that the response is correct
        self.assertEqual(response, "This is Paris, the capital of France.")
        
        # Check that the chat history was logged
        mock_log_chat.assert_called_once()
        
        # Check that the LLM was invoked with the correct messages
        args, _ = mock_chat_instance.invoke.call_args
        messages = args[0]
        
        # Check system message
        self.assertEqual(messages[0].content, "You are a helpful assistant.")
        
        # Check human message
        self.assertEqual(messages[1].content, "Hello, my name is Alice. What's the capital of France?")

    @patch('tlc.llm.simple_chat_chain._get_anthropic_api_key')
    @patch('tlc.llm.simple_chat_chain.ChatAnthropic')
    def test_chat_clone(self, mock_chat_anthropic, mock_get_api_key):
        """Test that SimpleChat.clone works correctly."""
        mock_get_api_key.return_value = "fake-api-key"
        mock_chat_instance = MagicMock()
        mock_chat_anthropic.return_value = mock_chat_instance

        # Initialize chat
        original_chat = SimpleChat("You are a helpful assistant.")
        
        # Clone the chat
        cloned_chat = original_chat.clone()
        
        # Check that the system prompt is the same
        self.assertEqual(cloned_chat.system_prompt, original_chat.system_prompt)
        
        # Check that the history is a copy, not the same object
        self.assertEqual(cloned_chat.history, original_chat.history)
        self.assertIsNot(cloned_chat.history, original_chat.history)
        
        # Check that the LLM is the same object
        self.assertIs(cloned_chat.llm, original_chat.llm)


if __name__ == "__main__":
    unittest.main() 