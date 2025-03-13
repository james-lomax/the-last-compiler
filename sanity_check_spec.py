#!/usr/bin/env python3
"""
sanity-check-spec

This program is the first step in the slop compiler. It takes a specification file and checks
if it is well defined enough to be compiled into code, and generates a Q&A file to handle ambiguities.
"""

import os
import sys
import logging
import argparse
from logging.handlers import RotatingFileHandler
from pathlib import Path
import jinja2

# Import LangChain components
try:
    from langchain_anthropic import ChatAnthropic
    from langchain.schema import HumanMessage, SystemMessage
except ImportError:
    print("Error: Required packages not found. Please install with:")
    print("pip install langchain langchain-anthropic")
    sys.exit(1)

# Constants
SYSTEM_PROMPT = """
You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

The specification files should generally define:
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
"""

# Templates
SANITY_CHECK_TEMPLATE = """
Read the spec

{spec}

Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions?
"""

READINESS_CHECK_TEMPLATE = """
{% if q_and_a %}
Here is a Q&A from our last review of this document:

{q_and_a}{% endif %}

Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

We are allowed to make reasonable assumptions, but we must explain them.
"""

BUILD_QUESTION_TEMPLATE = """
In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else.
"""

UNANSWERED_QUESTIONS_TEMPLATE = """
Are there unanswered questions? Just answer yes or no, nothing else.
"""

QA_GENERATION_TEMPLATE = """
{% if q_and_a %}
Here is a Q&A from our last review of this document:

{q_and_a}{% endif %}

List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

Do not number the questions, just list them like this:

**Question**: {question}
  **Assumption**: {assumption}

If there is an **Answer** from the last review, you must keep it the same.
"""

def setup_logging(module_name):
    """Set up logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Ensure slop/logs directory exists
    log_dir = Path("slop/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # File handler (DEBUG level with rotation)
    try:
        file_handler = RotatingFileHandler(
            f"slop/logs/{module_name}.log",
            maxBytes=1024*1024,  # 1MB
            backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Failed to set up file logging: {e}. Falling back to console logging only.")
    
    return logger

def check_api_key():
    """Check if the Anthropic API key file exists."""
    api_key_file = Path(".anthropic_key")
    if not api_key_file.exists():
        print("Error: .anthropic_key file not found.")
        print("Please create this file with your Anthropic API key.")
        sys.exit(1)
    
    return api_key_file.read_text().strip()

def setup_chat_model(api_key):
    """Set up the ChatAnthropic model."""
    try:
        chat_model = ChatAnthropic(
            anthropic_api_key=api_key,
            model="claude-3-7-sonnet-latest",
            temperature=0,
            timeout=60  # 60 second timeout
        )
        return chat_model
    except Exception as e:
        print(f"Error setting up ChatAnthropic model: {e}")
        sys.exit(1)

def read_spec_file(spec_file_path):
    """Read the specification file."""
    try:
        with open(spec_file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Specification file '{spec_file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading specification file: {e}")
        sys.exit(1)

def read_qa_file(qa_file_path):
    """Read the Q&A file if it exists."""
    if not os.path.exists(qa_file_path):
        return None
    
    try:
        with open(qa_file_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read existing Q&A file: {e}")
        return None

def write_qa_file(qa_file_path, content):
    """Write the Q&A file."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(qa_file_path), exist_ok=True)
        
        with open(qa_file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing Q&A file: {e}")
        return False

def render_template(template_str, **kwargs):
    """Render a Jinja2 template."""
    try:
        template = jinja2.Template(template_str)
        return template.render(**kwargs)
    except Exception as e:
        print(f"Error rendering template: {e}")
        sys.exit(1)

def chat_with_model(chat_model, system_prompt, user_prompt, logger):
    """Send a prompt to the chat model and get a response."""
    try:
        logger.debug(f"Sending prompt to model: {user_prompt}")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = chat_model.invoke(messages)
        
        logger.debug(f"Received response: {response.content}")
        return response.content
    except Exception as e:
        logger.error(f"Error communicating with language model: {e}")
        print(f"Error: Failed to get response from language model: {e}")
        sys.exit(1)

def validate_module_name(module_name):
    """Validate that the module name follows the required format."""
    if not module_name or not module_name.replace('-', '').isalnum() or not all(c.isalnum() or c == '-' for c in module_name):
        print(f"Error: Invalid module name '{module_name}'. Module name should be of the form 'module-name'.")
        sys.exit(1)
    return module_name

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Check if a specification is well defined enough to be compiled into code.")
    parser.add_argument("spec_file", help="Path to the specification file (markdown)")
    args = parser.parse_args()
    
    # Extract module name from spec file
    spec_file_path = args.spec_file
    module_name = os.path.splitext(os.path.basename(spec_file_path))[0]
    
    # Validate module name
    module_name = validate_module_name(module_name)
    
    # Set up logging
    logger = setup_logging(module_name)
    logger.info(f"Starting sanity check for module: {module_name}")
    
    # Check for API key
    api_key = check_api_key()
    
    # Set up chat model
    chat_model = setup_chat_model(api_key)
    
    # Read the spec file
    logger.info(f"Reading specification file: {spec_file_path}")
    spec_content = read_spec_file(spec_file_path)
    
    # Read existing Q&A file if it exists
    qa_file_path = f"slop/{module_name}.questions.md"
    existing_qa = read_qa_file(qa_file_path)
    
    # Step 1: Sanity check the spec
    logger.info("Performing initial sanity check")
    sanity_check_prompt = render_template(SANITY_CHECK_TEMPLATE, spec=spec_content)
    sanity_check_response = chat_with_model(chat_model, SYSTEM_PROMPT, sanity_check_prompt, logger)
    
    # Step 2: Check if the spec is ready to be built
    logger.info("Checking if spec is ready to be built")
    readiness_check_prompt = render_template(READINESS_CHECK_TEMPLATE, q_and_a=existing_qa)
    explanation = chat_with_model(chat_model, SYSTEM_PROMPT, readiness_check_prompt, logger)
    
    # Step 3: Get a yes/no answer on whether to build
    logger.info("Getting build decision")
    build_prompt = render_template(BUILD_QUESTION_TEMPLATE)
    build_response = chat_with_model(chat_model, SYSTEM_PROMPT, build_prompt, logger)
    build_failed = build_response.lower().strip() == "no"
    
    # Step 4: Check if there are unanswered questions
    logger.info("Checking for unanswered questions")
    questions_prompt = render_template(UNANSWERED_QUESTIONS_TEMPLATE)
    questions_response = chat_with_model(chat_model, SYSTEM_PROMPT, questions_prompt, logger)
    unanswered_questions = questions_response.lower().strip() == "yes"
    
    # Step 5: Generate Q&A file if needed
    if unanswered_questions:
        logger.info("Generating Q&A file")
        qa_prompt = render_template(QA_GENERATION_TEMPLATE, q_and_a=existing_qa)
        q_and_a = chat_with_model(chat_model, SYSTEM_PROMPT, qa_prompt, logger)
        
        # Create the Q&A file
        qa_content = f"# Questions and Answers for {module_name}\n\n{q_and_a}"
        success = write_qa_file(qa_file_path, qa_content)
        if success:
            logger.info(f"Q&A file written to: {qa_file_path}")
        else:
            logger.error("Failed to write Q&A file")
    
    # Output the result
    if build_failed:
        print("\nThe specification cannot be built yet:")
        print(explanation)
        if unanswered_questions:
            print(f"\nA Q&A file has been generated at: {qa_file_path}")
        sys.exit(1)
    else:
        print("\nThe specification is ready to be built!")
        print(explanation)
        sys.exit(0)

if __name__ == "__main__":
    main() 