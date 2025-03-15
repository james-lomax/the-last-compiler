#!/usr/bin/env python3
"""
Sanity check a specification file to determine if it's ready to be compiled into code.

This program is the first step in the-last-compiler. It takes a specification file and checks
if it is well defined enough to be compiled into code, and generates a Q&A file to handle ambiguities.
"""

import os
import sys
import logging
from dataclasses import dataclass
from pathlib import Path
import jinja2

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.specification_document import preprocess_spec_context, get_code_target
from tlc.llm.langchain_logging import save_logs

# Configure logging
logger = logging.getLogger("sanity_check_spec")

@dataclass
class CheckedSpecification:
    """Result of a sanity check on a specification."""
    module_name: str
    code_target_path: str
    no_context_spec: str
    q_and_a: str

def setup_logging(module_name: str):
    """Set up logging for the sanity check process."""
    # Create logs directory if it doesn't exist
    log_dir = Path("tlc/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure file handler
    file_handler = logging.FileHandler(f"tlc/logs/{module_name}.log")
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Configure logger
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Set console handler to INFO level
    console_handler.setLevel(logging.INFO)

def sanity_check_spec(spec_path: str) -> CheckedSpecification | None:
    """
    Check if a specification is ready to be implemented.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        A CheckedSpecification object if the spec is ready to implement, None otherwise
    """
    # Extract module name from spec path
    module_name = Path(spec_path).stem
    
    # Set up logging
    setup_logging(module_name)
    
    logger.info(f"Sanity checking specification: {spec_path}")
    
    try:
        # Check if the document has a code target
        code_target = get_code_target(spec_path)
        if not code_target:
            logger.info("No need to compile this document because it contains no code target.")
            return None
        
        # Preprocess the spec to be context-free
        logger.info("Preprocessing specification to be context-free")
        no_context_spec = preprocess_spec_context(spec_path)
        
        # Save the context-free spec
        no_context_path = f"tlc/{module_name}.no-context.md"
        with open(no_context_path, "w") as f:
            f.write(no_context_spec)
        logger.info(f"Saved context-free spec to {no_context_path}")
        
        # Create the system prompt
        system_prompt = """
You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

The specification files should generally define:
- Dependencies on other modules (named like [[path/to/module]])
- The interface this module exposes and how it is used
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
"""
        
        # Initialize the chat model
        chat = SimpleChat(system_prompt, model="claude-sonnet")
        
        # Check for existing Q&A file
        q_and_a = ""
        q_and_a_path = f"tlc/{module_name}.questions.md"
        if os.path.exists(q_and_a_path):
            with open(q_and_a_path, "r") as f:
                q_and_a = f.read()
        
        # Run the sanity check chat chain
        logger.debug("Starting sanity check chat chain")
        
        # First prompt - sanity check
        sanity_check_template = """
Read the spec:

======= BEGIN {{module_name}} spec =======
{{spec}}
======== END {{module_name}} spec ========

Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions? Are there references to concepts that are not yet defined and understood?

Do not try to write the code yet. Just describe any weaknesses you see in the specification.
"""
        
        sanity_check_response = chat.call(
            sanity_check_template,
            module_name=module_name,
            spec=no_context_spec
        )
        logger.debug(f"Sanity check response: {sanity_check_response}")
        
        # Second prompt - check if we have enough information
        enough_info_template = """
{% if q_and_a %}
Here is a Q&A from our last review of this document:

{q_and_a}{% endif %}

Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

We are allowed to make reasonable assumptions, but we must explain them.

Do not try to write the code yet. Just explain why this will work or not.
"""
        
        explanation = chat.call(
            enough_info_template,
            q_and_a=q_and_a
        )
        logger.debug(f"Explanation: {explanation}")
        
        # Third prompt - should we build this?
        build_prompt = "In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else."
        build_response = chat.call(build_prompt)
        logger.debug(f"Build response: {build_response}")
        
        build_failed = build_response.lower().strip() == "no"
        
        if build_failed:
            logger.info("Sanity check failed. The specification needs improvement.")
        
        # Fourth prompt - are there unanswered questions?
        questions_prompt = "Are there unanswered questions? Just answer yes or no, nothing else."
        questions_response = chat.call(questions_prompt)
        logger.debug(f"Questions response: {questions_response}")
        
        has_questions = questions_response.lower().strip() == "yes"
        
        # If there are questions, generate a Q&A file
        if has_questions:
            logger.info("Generating Q&A file")
            
            questions_template = """
List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

Do not number the questions, just list them like this:

**Question**: {question}
  **Assumption**: {assumption}

If there is an **Answer** from the last review, you must keep it the same.

If there is no reasonable way to answer the question, do not make an assumption, just state that you don't know. If you're unsure about a particular assumption, say so.
"""
            
            q_and_a = chat.call(questions_template)
            
            # Save the Q&A file
            with open(q_and_a_path, "w") as f:
                f.write(q_and_a)
            logger.info(f"Saved Q&A file to {q_and_a_path}")
            
            # If build failed, ask which questions are critical
            if build_failed:
                critical_questions_prompt = "Which questions are critical to answer in order to build this module?"
                critical_questions = chat.call(critical_questions_prompt)
                logger.info(f"Critical questions to answer:\n{critical_questions}")
        
        # Return the result
        if not build_failed:
            code_target_path = module_name.replace("-", "_") + ".py"
            return CheckedSpecification(
                module_name=module_name,
                code_target_path=code_target_path,
                no_context_spec=no_context_spec,
                q_and_a=q_and_a
            )
        else:
            return None
    
    except Exception as e:
        logger.error(f"Error during sanity check: {e}", exc_info=True)
        return None
    finally:
        # Save logs
        save_logs()

def main():
    """Command-line interface for sanity checking a specification."""
    if len(sys.argv) != 2:
        print("Usage: sanity-check-spec module-name.md")
        sys.exit(1)
    
    spec_path = sys.argv[1]
    
    try:
        result = sanity_check_spec(spec_path)
        if result:
            print(f"Specification is ready to implement as {result.code_target_path}")
            sys.exit(0)
        else:
            print("Specification is not ready to implement.")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 