# simple_chat_chain.py

## Usage

Example:

```python
from tlc.simple_chat_chain import SimpleChat

chat = SimpleChat(system_prompt)

question_template = "Hello, my name is {{ name }}. {{ question }}"

capital_of_france = chat.call(
  question_template,
  {
    "name": "Alice",
    "question": "What's the capital of France?"
  }
)

population_paris = chat.call(
  question_template,
  {
    "name": "Alice",
    "question": "What's the population of Paris?"
  }
)
```

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

We will use langchain-anthropic to implement the SimpleChat class. This class will instantiate a ChatAnthropic object, reading the API key from the .anthropic_key file (which should be read from the current directory or, if not found, from the users home directory).

Instantiate ChatAnthropic with:

```python
ChatAnthropic(
    model="claude-3-7-sonnet-latest",
    api_key=api_key,
)
```
