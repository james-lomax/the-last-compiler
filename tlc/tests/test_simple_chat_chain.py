import sys
import os
import unittest

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simple_chat_chain import SimpleChat

class TestSimpleChat(unittest.TestCase):
    def test_simple_chat_example(self):
        """
        This is a simple example of how to use the SimpleChat class.
        Note: This test will make actual API calls to Anthropic if run.
        """
        # Create a new chat session
        chat = SimpleChat(system_prompt="You are a helpful AI assistant.")
        
        # Define a template and input
        template = "Hello, my name is {{ name }}. {{ question }}"
        input_data = {
            "name": "Alice",
            "question": "What's the capital of France?"
        }
        
        # Call the model (commented out to avoid making API calls during tests)
        # response = chat.call(template, input_data)
        # print(f"Response: {response}")
        
        # Test forking the conversation
        forked_chat = chat.clone()
        
        # The original chat and forked chat should have the same history initially
        self.assertEqual(len(chat.history), len(forked_chat.history))
        
        # But they should be different objects
        self.assertIsNot(chat, forked_chat)
        self.assertIsNot(chat.history, forked_chat.history)

if __name__ == "__main__":
    unittest.main() 