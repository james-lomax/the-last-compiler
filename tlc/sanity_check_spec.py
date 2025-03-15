#!/usr/bin/env python3
"""
Sanity check for specification files.

This program checks if a specification file is well defined enough to be compiled into code,
and generates a Q&A file to handle ambiguities.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.specification_document import preprocess_spec_context
from tlc.llm.langchain_logging import save_logs

# Configure logging
def setup_logging(module_name: str):
    """Set up logging for the module."""
    # Create logs directory if it doesn't exist
    log_dir = Path("tlc/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure file handler
    file_handler = logging.FileHandler(log_dir / f"{module_name}.log")
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

def get_module_name(spec_path: str) -> str:
    """
    Extract the module name from the specification file path.
    
    Args:
        spec_path: Path to the specification file
        
    Returns:
        The module name
    """
    # Get the filename without extension
    filename = os.path.basename(spec_path)
    module_name = os.path.splitext(filename)[0]
    return module_name

def read_qa_file(module_name: str) -> Optional[str]:
    """
    Read the Q&A file if it exists.
    
    Args:
        module_name: The module name
        
    Returns:
        The content of the Q&A file or None if it doesn't exist
    """
    qa_path = Path(f"tlc/{module_name}.questions.md")
    if qa_path.exists():
        with open(qa_path, "r") as f:
            return f.read()
    return None

def write_qa_file(module_name: str, content: str):
    """
    Write the Q&A file.
    
    Args:
        module_name: The module name
        content: The content to write
    """
    qa_path = Path(f"tlc/{module_name}.questions.md")
    with open(qa_path, "w") as f:
        f.write(content)
    logging.info(f"Updated Q&A file: {qa_path}")

def write_context_free_spec(module_name: str, content: str):
    """
    Write the context-free specification file.
    
    Args:
        module_name: The module name
        content: The content to write
    """
    spec_path = Path(f"tlc/{module_name}.no-context.md")
    with open(spec_path, "w") as f:
        f.write(content)
    logging.info(f"Updated context-free spec file: {spec_path}")

def sanity_check_spec(spec_path: str):
    """
    Check if a specification file is well defined enough to be compiled into code.
    
    Args:
        spec_path: Path to the specification file
    """
    module_name = get_module_name(spec_path)
    logger = setup_logging(module_name)
    
    try:
        logger.info(f"Processing specification file: {spec_path}")
        
        # Preprocess the spec to be context-free
        logger.info("Preprocessing spec to be context-free")
        context_free_spec = preprocess_spec_context(spec_path)
        write_context_free_spec(module_name, context_free_spec)
        
        # Read the Q&A file if it exists
        q_and_a = read_qa_file(module_name)
        
        # Create the chat model
        system_prompt = """
        You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

        The specification files should generally define:
        - Dependencies on other modules (named like @path/to/module.md)
        - the inputs and outputs of the program
        - the command arguments of the program
        - how the program is implemented

        Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
        """
        
        chat = SimpleChat(system_prompt, model="claude-sonnet")
        
        # Step 1: Sanity check the spec
        logger.info("Performing initial sanity check")
        prompt = f"Read the spec\n\n{context_free_spec}\n\nIs it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions? Are there references to concepts that are not yet defined and understood?"
        response = chat.call(prompt)
        logger.debug(f"Sanity check response:\n{response}")
        
        # Step 2: Ask if we have enough information
        logger.info("Checking if we have enough information to implement")
        prompt_template = """
        {% if q_and_a %}
        Here is a Q&A from our last review of this document:

        {q_and_a}{% endif %}

        Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

        We are allowed to make reasonable assumptions, but we must explain them.
        """
        
        prompt = prompt_template.replace("{q_and_a}", q_and_a if q_and_a else "")
        if "{% if q_and_a %}" in prompt:
            # Handle the Jinja2 template manually since we're not using Jinja2 here
            if q_and_a:
                prompt = prompt.replace("{% if q_and_a %}", "")
                prompt = prompt.replace("{% endif %}", "")
            else:
                # Remove the entire conditional block
                start_idx = prompt.find("{% if q_and_a %}")
                end_idx = prompt.find("{% endif %}") + len("{% endif %}")
                prompt = prompt[:start_idx] + prompt[end_idx:]
        
        explanation = chat.call(prompt)
        logger.debug(f"Information check response:\n{explanation}")
        
        # Step 3: Should we build this?
        logger.info("Determining if we should build this")
        response = chat.call("In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else.")
        build_failed = response.lower().strip() == "no"
        logger.debug(f"Build decision: {'No' if build_failed else 'Yes'}")
        
        # Step 4: Are there unanswered questions?
        logger.info("Checking for unanswered questions")
        response = chat.call("Are there unanswered questions? Just answer yes or no, nothing else.")
        has_questions = response.lower().strip() == "yes"
        logger.debug(f"Has unanswered questions: {'Yes' if has_questions else 'No'}")
        
        # Step 5: Generate Q&A file if needed
        if has_questions:
            logger.info("Generating Q&A file")
            prompt = """
            List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

            Do not number the questions, just list them like this:

            **Question**: {question}
              **Assumption**: {assumption}

            If there is an **Answer** from the last review, you must keep it the same.
            """
            
            qa_content = chat.call(prompt)
            write_qa_file(module_name, qa_content)
        
        # Print summary
        if build_failed:
            logger.info("RESULT: The specification needs improvement before it can be built.")
            logger.info(f"Explanation: {explanation}")
        else:
            logger.info("RESULT: The specification is ready to be built.")
        
        if has_questions:
            logger.info(f"Questions and assumptions have been written to tlc/{module_name}.questions.md")
    
    finally:
        # Save logs
        save_logs()

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description="Check if a specification file is well defined enough to be compiled into code.")
    parser.add_argument("spec_path", help="Path to the specification file")
    
    args = parser.parse_args()
    
    sanity_check_spec(args.spec_path)

if __name__ == "__main__":
    main() 