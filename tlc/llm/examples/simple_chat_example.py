"""
Example usage of the SimpleChat class.
"""

import sys
import os

# Add the parent directory to the path so we can import the tlc package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from tlc.llm import SimpleChat, save_logs


def main():
    """
    Demonstrate the usage of SimpleChat with a simple conversation.
    """
    try:
        # Initialize the chat with a system prompt
        system_prompt = "You are a helpful, concise assistant that specializes in geography."
        chat = SimpleChat(system_prompt, model="claude-sonnet")
        
        # Define a template for our questions
        question_template = "Hello, my name is {{ name }}. {{ question }}"
        
        # Ask about the capital of France
        print("Asking about the capital of France...")
        capital_response = chat.call(
            question_template,
            name="Alice",
            question="What's the capital of France?"
        )
        print(f"Response: {capital_response}\n")
        
        # Ask a follow-up question about the population of Paris
        print("Asking about the population of Paris...")
        population_response = chat.call(
            question_template,
            name="Alice",
            question="What's the population of Paris?"
        )
        print(f"Response: {population_response}\n")
        
        # Clone the chat and ask a different question in a new conversation branch
        print("Cloning the chat and asking about the capital of Japan...")
        cloned_chat = chat.clone()
        japan_response = cloned_chat.call(
            question_template,
            name="Bob",
            question="What's the capital of Japan?"
        )
        print(f"Response: {japan_response}\n")
        
        # Continue the original conversation
        print("Continuing the original conversation...")
        landmarks_response = chat.call(
            question_template,
            name="Alice",
            question="What are some famous landmarks in Paris?"
        )
        print(f"Response: {landmarks_response}\n")
        
        print("Conversation completed successfully!")
    finally:
        # Make sure to save the logs
        save_logs()


if __name__ == "__main__":
    main() 