#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from pathlib import Path

from jinja2 import Template
from tlc.simple_chat_chain import SimpleChat

# Configure logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(message)s'))

file_handler = None  # Will be set up once we know the module name

logger = logging.getLogger('sanity-check-spec')
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

SYSTEM_PROMPT = """
You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

The specification files should generally define:
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
"""

def setup_file_logging(module_name: str):
    global file_handler
    log_dir = Path('slop/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(f'slop/logs/{module_name}.log')
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(file_handler)

def read_qa_file(module_name: str) -> str:
    qa_path = Path(f'slop/{module_name}.questions.md')
    if not qa_path.exists():
        return ""
    return qa_path.read_text()

def write_qa_file(module_name: str, content: str):
    qa_path = Path(f'slop/{module_name}.questions.md')
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(content)
    logger.info(f"Updated Q&A file: {qa_path}")

def main():
    parser = argparse.ArgumentParser(description='Sanity check a specification file')
    parser.add_argument('spec_file', help='The specification file to check')
    args = parser.parse_args()

    # Extract module name from spec file
    module_name = Path(args.spec_file).stem

    # Setup logging
    setup_file_logging(module_name)

    # Read the spec file
    try:
        spec_content = Path(args.spec_file).read_text()
    except FileNotFoundError:
        logger.error(f"Specification file not found: {args.spec_file}")
        sys.exit(1)

    # Read existing Q&A if it exists
    qa_content = read_qa_file(module_name)

    # Initialize chat
    chat = SimpleChat(SYSTEM_PROMPT)
    
    # First sanity check
    logger.info("Performing initial sanity check...")
    logger.debug("Sending initial sanity check prompt")
    response = chat.call(
        "Read the spec\n\n{spec}\n\nIs it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions?",
        {"spec": spec_content}
    )
    logger.debug(f"Response: {response}")

    # Check if we have enough information
    logger.info("Checking if we have enough information...")
    prompt_template = """
    {% if q_and_a %}
    Here is a Q&A from our last review of this document:

    {q_and_a}{% endif %}

    Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

    We are allowed to make reasonable assumptions, but we must explain them.
    """
    explanation = chat.call(
        prompt_template,
        {"q_and_a": qa_content}
    )
    logger.debug(f"Explanation: {explanation}")

    # Should we build?
    build_response = chat.call(
        "In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else.",
        {}
    )
    build_failed = build_response.lower().strip() == "no"

    # Check for questions
    questions_response = chat.call(
        "Are there unanswered questions? Just answer yes or no, nothing else.",
        {}
    )
    has_questions = questions_response.lower().strip() == "yes"

    if has_questions:
        logger.info("Generating Q&A file...")
        qa_response = chat.call(
            """List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

            Do not number the questions, just list them like this:

            **Question**: {question}
              **Assumption**: {assumption}

            If there is an **Answer** from the last review, you must keep it the same.""",
            {}
        )
        write_qa_file(module_name, qa_response)

    if build_failed:
        logger.info("Specification needs improvement. Check the Q&A file for details.")
        sys.exit(1)
    else:
        logger.info("Specification is ready to be implemented.")

if __name__ == '__main__':
    main() 