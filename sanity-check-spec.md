# sanity-check-spec.py

This program is the first step in the slop compiler. It takes a specification file and checks if it is well defined enough to be compiled into code, and generates a Q&A file to handle ambiguities.

The program works by reading an input markdown file, and performing several prompts using a langchain ChatModel (specifically Claude 3.7 Sonnet), determining what the questions that need answering are, providing assumptions where possible, deciding whether the spec is ready to be compiled into code, and if not, explaining why.

Usage:

```
sanity-check-spec module-name.md
```

## Import interfaces

- See @simple-chat-chain.md for information how to use the SimpleChat interface to interact with the language model.

## Module name

The module name is of the form `module-name`. This refers to a module defined in `module-name.md`, and implemented in `module_name.py`.

## Language Model

The program uses the `claude-3-7-sonnet-latest` model via the LangChain ChatAnthropic interface and @simple-chat-chain.md. The API key should be stored in a file named `.anthropic_key` in the root directory.

Always implement these prompts verbatim, using jinja2 templates.

## System prompt

This system prompt is used in all the following chat prompt steps.

```
You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

The specification files should generally define:
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
```

## Chat chain - Sense check and Q&A prep

The following section describes the precise prompts we should use with the Chatmodel.

First ask the AI to sanity check the spec.

```jinja2
Read the spec

{spec}

Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions?
```

We will log the chain of thought here in the debug log, but not print to the console.

Prompt the AI to think about things that are unclear:

```jinja2
{% if q_and_a %}
Here is a Q&A from our last review of this document:

{q_and_a}{% endif %}

Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

We are allowed to make reasonable assumptions, but we must explain them.
```

let explanation = response

```jinja2
In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else.
```

let build_failed = response is "no"

```jinja2
Are there unanswered questions? Just answer yes or no, nothing else.
```

If there are unanswered questions, we need to generate a q&a file.

```jinja2
List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

Do not number the questions, just list them like this:

**Question**: {question}
  **Assumption**: {assumption}

If there is an **Answer** from the last review, you must keep it the same.
```

Store response in `slop/${module_name}.questions.md` - overwrite if it exists.

## Logging

Use the standard logging library. Logging in the CLI is INFO by default, but we store in `slop/logs/${module_name}.log`. The format of the logs in the console will be to just show the message and nothing else. The format of the logs in the file will include the timestamp, logger name, log level and message.

- Log chat prompts and responses between the AI and user with log level `DEBUG`.
- Log the step we're doing as level `INFO`.
- Log the files we update as level `INFO`.

## Coding notes

- There should be minimal error checking in this program
