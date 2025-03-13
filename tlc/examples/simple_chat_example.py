import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simple_chat_chain import SimpleChat

def main():
    """
    Example of using SimpleChat for a multi-turn conversation.
    """
    # Create a new chat session with a system prompt
    chat = SimpleChat(system_prompt="""
    You are a helpful AI assistant specialized in explaining programming concepts.
    Keep your explanations concise and provide simple examples when appropriate.
    """)
    
    # First interaction
    template1 = "Can you explain what {{ concept }} is in programming?"
    input1 = {"concept": "recursion"}
    
    print("User: Can you explain what recursion is in programming?")
    response1 = chat.call(template1, input1)
    print(f"AI: {response1}\n")
    
    # Second interaction (continuing the conversation)
    template2 = "Can you provide a simple {{ language }} example of {{ concept }}?"
    input2 = {"language": "Python", "concept": "recursion"}
    
    print("User: Can you provide a simple Python example of recursion?")
    response2 = chat.call(template2, input2)
    print(f"AI: {response2}\n")
    
    # Fork the conversation to ask about a different concept
    forked_chat = chat.clone()
    
    # Continue with original chat
    template3 = "What are some common pitfalls with {{ concept }}?"
    input3 = {"concept": "recursion"}
    
    print("User: What are some common pitfalls with recursion?")
    response3 = chat.call(template3, input3)
    print(f"AI: {response3}\n")
    
    # Use the forked chat to ask about a different concept
    template4 = "Now, can you explain what {{ concept }} is?"
    input4 = {"concept": "closures"}
    
    print("--- Forked conversation ---")
    print("User: Now, can you explain what closures is?")
    response4 = forked_chat.call(template4, input4)
    print(f"AI: {response4}\n")

if __name__ == "__main__":
    main() 