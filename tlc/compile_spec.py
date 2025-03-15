#!/usr/bin/env python3
"""
Compile a specification file into code.

This program is the second step in the-last-compiler. It takes a specification file that has
passed the sanity check and compiles it into code.
"""

import os
import sys
import logging
from pathlib import Path

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.sanity_check_spec import sanity_check_spec, CheckedSpecification
from tlc.llm.langchain_logging import save_logs

# Configure logging
logger = logging.getLogger("compile_spec")

def setup_logging(module_name: str):
    """Set up logging for the compile process."""
    # Create logs directory if it doesn't exist
    log_dir = Path("tlc/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure file handler
    file_handler = logging.FileHandler(f"tlc/logs/{module_name}.compile.log")
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

def compile_spec(spec_path: str) -> bool:
    """
    Compile a specification into code.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        True if compilation succeeded, False otherwise
    """
    # Extract module name from spec path
    module_name = Path(spec_path).stem
    
    # Set up logging
    setup_logging(module_name)
    
    logger.info(f"Compiling specification: {spec_path}")
    
    try:
        # First run the sanity check
        logger.info("Running sanity check...")
        checked_spec = sanity_check_spec(spec_path)
        
        if not checked_spec:
            logger.info("Sanity check failed. Cannot compile.")
            return False
        
        logger.info(f"Sanity check passed. Compiling to {checked_spec.code_target_path}...")
        
        # Create the system prompt
        system_prompt = """
You are a highly skilled Python software engineer. Your job is to read module specifications that describe the implementation of a Python module and turn it into clean, working code.

The specification files should generally define:
- Dependencies on other modules (named like [[path/to/module]])
- The interface this module exposes and how it is used
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
"""
        
        # Initialize the chat model
        chat = SimpleChat(system_prompt, debug_name=f"{spec_path}.compile", model="claude-sonnet")
        
        # One-shot code generation
        code_generation_template = """
Consider the following specification:

====== BEGIN {{checked_spec.module_name}} specification ======
{{checked_spec.no_context_spec}}
====== END {{checked_spec.module_name}} specification ======

We have reviewed this specification, and discussed some clarifications in this Q&A:

{{checked_spec.q_and_a}}

The specification is ready to implement in {{checked_spec.code_target_path}}. Write the code for this module. Do not write anything else, just the code.

Do not include the markdown back-ticks, we're going to output this straight to {{checked_spec.code_target_path}}.
"""
        
        logger.info("Generating code...")
        code = chat.call(
            code_generation_template,
            checked_spec=checked_spec
        )
        logger.debug(f"Generated code:\n{code}")
        
        # Save the generated code
        code_path = f"tlc/{checked_spec.code_target_path}"
        with open(code_path, "w") as f:
            f.write(code)
        logger.info(f"Saved generated code to {code_path}")
        
        # Code review step
        logger.info("Reviewing code...")
        code_review_template = """
Consider the following specification:

====== BEGIN {{checked_spec.module_name}} specification ======
{{checked_spec.no_context_spec}}
====== END {{checked_spec.module_name}} specification ======

Here is our implementation:

====== BEGIN {{checked_spec.code_target_path}} implementation ======
{{code}}
====== END {{checked_spec.code_target_path}} implementation ======

Review this implementation. Is it complete? Is it valid code? Does it meet our specifications expectations?
"""
        
        review = chat.call(
            code_review_template,
            checked_spec=checked_spec,
            code=code
        )
        logger.debug(f"Code review:\n{review}")
        
        # Check if the implementation is ready
        ready_prompt = "Answering only yes or no, is this implementation ready to use?"
        ready_response = chat.call(ready_prompt)
        logger.debug(f"Ready response: {ready_response}")
        
        is_ready = ready_response.lower().strip() == "yes"
        
        if is_ready:
            logger.info("Compile succeeded.")
            return True
        else:
            logger.info("Compile succeeded but the implementation may have issues.")
            
            # Get suggestions for improvement
            suggestions_prompt = "Summarise why this implementation is not ready. Briefly give some suggestions as to how we might improve the specification to fix this."
            suggestions = chat.call(suggestions_prompt)
            logger.info(f"Suggestions for improvement:\n{suggestions}")
            
            return False
    
    except Exception as e:
        logger.error(f"Error during compilation: {e}", exc_info=True)
        return False
    finally:
        # Save logs
        save_logs()

def main():
    """Command-line interface for compiling a specification."""
    if len(sys.argv) != 2:
        print("Usage: compile-spec module-name.md")
        sys.exit(1)
    
    spec_path = sys.argv[1]
    
    try:
        success = compile_spec(spec_path)
        if success:
            print("Compile succeeded.")
            sys.exit(0)
        else:
            print("Compile failed or produced code with issues.")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 