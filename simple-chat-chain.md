# simple_chat_chain.py

## Interface

Define a really simple chat interface that allows for chat style interaction chains with the anthropic LLM.

```python
class SimpleChat:
    def __init__(self, system_prompt: str):
        pass

    def call(self, prompt_template: str, input: dict) -> str:
        pass

    def clone(self) -> 'Chat':
        pass
```

## Implementation

- SimpleChat maintains a history internally
- SimpleChat.call will render the prompt template (using Jinja2) with the input and append the response to the history, then invoke the model, add the response to the history and return the response
- SimpleChat.clone will copy itself such that we can fork the chat session and continue the conversation in two different directions

We will use langchain-anthropic to implement the SimpleChat class. This class will instantiate a ChatAnthropic object, reading the API key from a local .anthropic_key file.
