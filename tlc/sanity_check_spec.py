#!/usr/bin/env python3
"""
sanity-check-spec.py

This program is the first step in the slop compiler. It takes a specification file and checks if it is
well defined enough to be compiled into code, and generates a Q&A file to handle ambiguities.
"""

import os
import sys
import logging
import re
from pathlib import Path

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.specification_document import preprocess_spec_context

# Set up logging
def setup_logging(module_name):
    """Set up logging for the program."""
    # Create logs directory if it doesn't exist
    log_dir = Path("slop/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up file handler
    file_handler = logging.FileHandler(f"slop/logs/{module_name}.log")
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Set up logger
    logger = logging.getLogger(f"sanity_check_spec.{module_name}")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def main():
    """Main function for the sanity-check-spec program."""
    if len(sys.argv) != 2:
        print("Usage: sanity-check-spec module-name.md")
        sys.exit(1)
    
    spec_path = sys.argv[1]
    
    # Extract module name from spec path
    module_name_match = re.match(r'(.+)\.md$', os.path.basename(spec_path))
    if not module_name_match:
        print(f"Error: Specification file must have a .md extension: {spec_path}")
        sys.exit(1)
    
    module_name = module_name_match.group(1)
    
    # Set up logging
    logger = setup_logging(module_name)
    logger.info(f"Processing specification: {spec_path}")
    
    # Create slop directory if it doesn't exist
    slop_dir = Path("slop")
    slop_dir.mkdir(exist_ok=True)
    
    # Build spec with context
    logger.info("Building spec with context")
    try:
        spec_with_context = preprocess_spec_context(spec_path)
        context_free_spec_path = f"slop/{module_name}.no-context.md"
        with open(context_free_spec_path, "w") as f:
            f.write(spec_with_context)
        logger.info(f"Created context-free spec: {context_free_spec_path}")
    except Exception as e:
        logger.error(f"Error building spec with context: {e}")
        sys.exit(1)
    
    # Read the spec file
    try:
        with open(context_free_spec_path, "r") as f:
            spec_content = f.read()
    except Exception as e:
        logger.error(f"Error reading spec file: {e}")
        sys.exit(1)
    
    # Check if Q&A file exists
    q_and_a_path = f"slop/{module_name}.questions.md"
    q_and_a_content = None
    if os.path.exists(q_and_a_path):
        try:
            with open(q_and_a_path, "r") as f:
                q_and_a_content = f.read()
            logger.info(f"Found existing Q&A file: {q_and_a_path}")
        except Exception as e:
            logger.error(f"Error reading Q&A file: {e}")
    
    # System prompt for all chat interactions
    system_prompt = """You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

The specification files should generally define:
- Dependencies on other modules (named like @path/to/module.md)
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented."""
    
    # Create chat model
    chat = SimpleChat(system_prompt=system_prompt, model="claude-sonnet")
    
    # Sanity check the spec
    logger.info("Performing sanity check on the spec")
    sanity_check_prompt = """Read the spec

{spec}

Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions? Are there references to concepts that are not yet defined and understood?"""
    
    sanity_check_response = chat.call(sanity_check_prompt, spec=spec_content)
    logger.debug(f"Sanity check prompt:\n{sanity_check_prompt}")
    logger.debug(f"Sanity check response:\n{sanity_check_response}")
    
    # Check if we have enough information
    logger.info("Checking if we have enough information to implement the spec")
    enough_info_prompt = """{% if q_and_a %}
Here is a Q&A from our last review of this document:

{q_and_a}{% endif %}

Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

We are allowed to make reasonable assumptions, but we must explain them."""
    
    enough_info_response = chat.call(enough_info_prompt, q_and_a=q_and_a_content)
    logger.debug(f"Enough info prompt:\n{enough_info_prompt}")
    logger.debug(f"Enough info response:\n{enough_info_response}")
    explanation = enough_info_response
    
    # Check if we should build
    logger.info("Checking if we should build the spec")
    build_prompt = """In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else."""
    
    build_response = chat.call(build_prompt)
    logger.debug(f"Build prompt:\n{build_prompt}")
    logger.debug(f"Build response:\n{build_response}")
    build_failed = build_response.strip().lower() == "no"
    
    # Check if there are unanswered questions
    logger.info("Checking if there are unanswered questions")
    questions_prompt = """Are there unanswered questions? Just answer yes or no, nothing else."""
    
    questions_response = chat.call(questions_prompt)
    logger.debug(f"Questions prompt:\n{questions_prompt}")
    logger.debug(f"Questions response:\n{questions_response}")
    has_questions = questions_response.strip().lower() == "yes"
    
    # Generate Q&A file if needed
    if has_questions:
        logger.info("Generating Q&A file")
        qa_prompt = """List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

Do not number the questions, just list them like this:

**Question**: {question}
  **Assumption**: {assumption}

If there is an **Answer** from the last review, you must keep it the same."""
        
        qa_response = chat.call(qa_prompt)
        logger.debug(f"Q&A prompt:\n{qa_prompt}")
        logger.debug(f"Q&A response:\n{qa_response}")
        
        # Write Q&A file
        with open(q_and_a_path, "w") as f:
            f.write(qa_response)
        logger.info(f"Created Q&A file: {q_and_a_path}")
    
    # Print summary
    if build_failed:
        logger.info("The spec needs improvement before it can be built.")
        logger.info(f"Explanation: {explanation}")
    else:
        logger.info("The spec is ready to be built.")
    
    if has_questions:
        logger.info(f"Questions have been written to {q_and_a_path}")

if __name__ == "__main__":
    main() 