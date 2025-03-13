# langchain_logging.py

Provides a super simple logging interface for langchain, recording branching conversations so that we can clearly inspect what prompts were used and what the responses were.

## Interface

Define a python method:

```python
def log_chat(messages: List[BaseMessage]) -> None:
    pass

def save_logs() -> None:
    # Save to slop/logs/session/<timestamp>.json
    # Create the directory if it doesn't exist
    pass
```

## Implementation

log_chat will first render all messages into strings, by prepending the role to the message:

- AIMessage -> "AI: " + message
- HumanMessage -> "Human: " + message
- SystemMessage -> "System: " + message

Internally we define a logging interface that records all branches of the conversation:

```python
@dataclass_json
@dataclass
class ChatLogBranch:
    messages: List[str]
    branches: List['ChatLogBranch']
```

We maintain a global variable `log_branches` that is a list of `ChatLogBranch` objects.

Any time we call `log_chat`, we have to insert these messages into log_branches to maintain a tree structure. We compare the tree structure with the new chat chain and find the first message that is different. If necessary we create a branch in the ChatLogBranch to allow describing the multiple branches of the conversation.

### Tech notes

- @dataclass_json classes generate a to_dict method, which is used by the save_logs function to save the logs to a JSON file.

## Test

Construct a simple pytest test, e.g.:

```python
def test_log_chat():
    log_chat([HumanMessage(content="Hello"), AIMessage(content="Hello")])

    assert log_branches == [
        ChatLogBranch(messages=["Human: Hello", "AI: Hello"], branches=[])
    ]

    log_chat([HumanMessage(content="Hello"), AIMessage(content="What?")])

    assert log_branches == [
        ChatLogBranch(messages=["Human: Hello"], branches=[
            ChatLogBranch(messages=["Hello"], branches=[]),
            ChatLogBranch(messages=["AI: What?"], branches=[])
        ])
    ]

    # TODO More complicated case
```