#!/usr/bin/env python3
"""
Sanity Check Spec

This program is the first step in the slop compiler. It takes a specification file and checks
if it is well defined enough to be compiled into code, and generates a Q&A file to handle ambiguities.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.llm.langchain_logging import log_chat, save_logs
from tlc.specification_document import load_specification_document, describe_interface

# Configure logging
def setup_logging(module_name: str):
    """Set up logging for the program."""
    # Create logs directory if it doesn't exist
    log_dir = Path("slop/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure file handler
    file_handler = logging.FileHandler(f"slop/logs/{module_name}.log")
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_module_name_from_path(path: str) -> str:
    """Extract module name from file path."""
    base_name = os.path.basename(path)
    module_name = os.path.splitext(base_name)[0]
    return module_name

def read_qa_file(module_name: str) -> Optional[str]:
    """Read existing Q&A file if it exists."""
    qa_path = Path(f"slop/{module_name}.questions.md")
    if qa_path.exists():
        with open(qa_path, "r") as f:
            return f.read()
    return None

def write_qa_file(module_name: str, content: str):
    """Write Q&A file."""
    qa_path = Path(f"slop/{module_name}.questions.md")
    with open(qa_path, "w") as f:
        f.write(content)
    logging.info(f"Updated Q&A file: {qa_path}")

def build_spec_with_context(spec_path: str, module_name: str) -> str:
    """Build spec with interface context."""
    logging.info("Building spec with interface context")
    
    # Load the specification document
    spec = load_specification_document(spec_path)
    
    # Get the interface context
    interface_context = describe_interface(spec)
    
    # Create a new section with the interface context
    context_section = interface_context
    context_section.title = "Interface context"
    
    # Prepend the interface context to the spec
    spec.children.insert(0, context_section)
    
    # Convert the spec to markdown
    spec_with_context = str(spec)
    
    # Write the spec with context to a file
    context_path = Path(f"slop/{module_name}.context.md")
    with open(context_path, "w") as f:
        f.write(spec_with_context)
    
    logging.info(f"Created spec with context: {context_path}")
    
    return spec_with_context

def sanity_check_spec(spec_path: str):
    """Main function to sanity check a specification file."""
    module_name = get_module_name_from_path(spec_path)
    logger = setup_logging(module_name)
    
    try:
        # Build spec with context
        spec_with_context = build_spec_with_context(spec_path, module_name)
        
        # Read existing Q&A file if it exists
        q_and_a = read_qa_file(module_name)
        
        # System prompt for all chat interactions
        system_prompt = """
        You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

        The specification files should generally define:
        - Dependencies on other modules (named like @path/to/module.md)
        - the inputs and outputs of the program
        - the command arguments of the program
        - how the program is implemented

        Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
        """
        
        # Create chat instance
        chat = SimpleChat(system_prompt, model="claude-sonnet")
        
        # First prompt - Sanity check
        logging.info("Performing initial sanity check")
        prompt_template = """
        Read the spec

        {{spec}}

        Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions? Are there references to concepts that are not yet defined and understood?
        """
        
        response = chat.call(
            prompt_template,
            spec=spec_with_context
        )
        logging.debug(f"Sanity check response: {response}")
        
        # Second prompt - Check if we have enough information
        logging.info("Checking if we have enough information to implement")
        prompt_template = """
        {% if q_and_a %}
        Here is a Q&A from our last review of this document:

        {{q_and_a}}{% endif %}

        Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

        We are allowed to make reasonable assumptions, but we must explain them.
        """
        
        explanation = chat.call(
            prompt_template,
            q_and_a=q_and_a
        )
        logging.debug(f"Explanation: {explanation}")
        
        # Third prompt - Should we build this?
        logging.info("Determining if we should build this")
        prompt_template = """
        In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else.
        """
        
        build_response = chat.call(prompt_template)
        build_failed = build_response.lower().strip() == "no"
        logging.debug(f"Build response: {build_response}")
        
        # Fourth prompt - Are there unanswered questions?
        logging.info("Checking for unanswered questions")
        prompt_template = """
        Are there unanswered questions? Just answer yes or no, nothing else.
        """
        
        questions_response = chat.call(prompt_template)
        has_questions = questions_response.lower().strip() == "yes"
        logging.debug(f"Questions response: {questions_response}")
        
        # If there are unanswered questions, generate Q&A file
        if has_questions:
            logging.info("Generating Q&A file")
            prompt_template = """
            List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

            Do not number the questions, just list them like this:

            **Question**: {{question}}
              **Assumption**: {{assumption}}

            If there is an **Answer** from the last review, you must keep it the same.
            """
            
            qa_content = chat.call(prompt_template)
            write_qa_file(module_name, qa_content)
        
        # Print summary
        if build_failed:
            logging.info("Spec is not ready to be built. Please review the Q&A file and update the spec.")
        else:
            logging.info("Spec is ready to be built.")
        
        # Print explanation
        print("\nExplanation:")
        print(explanation)
        
    finally:
        # Save logs
        save_logs()

def main():
    """Entry point for the program."""
    parser = argparse.ArgumentParser(description="Sanity check a specification file.")
    parser.add_argument("spec_path", help="Path to the specification file")
    args = parser.parse_args()
    
    sanity_check_spec(args.spec_path)

if __name__ == "__main__":
    main() 