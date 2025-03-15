import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.specification_document import get_code_target

def setup_logging(module_name):
    """
    Set up logging for the compile process.
    
    Args:
        module_name: The name of the module being compiled
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("tlc/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up file handler
    log_file = log_dir / f"{module_name}.compile.log"
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def get_module_name(spec_path):
    """
    Extract the module name from the specification path.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        The module name without extension
    """
    return Path(spec_path).stem

def run_sanity_check(spec_path):
    """
    Run the sanity check on the specification.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        True if the sanity check passed, False otherwise
    """
    logging.info(f"Running sanity check on {spec_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "tlc.sanity_check_spec", spec_path],
            capture_output=True,
            text=True,
            check=True
        )
        logging.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Sanity check failed: {e.stderr}")
        return False

def compile_spec(spec_path):
    """
    Compile the specification into code.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        True if compilation succeeded, False otherwise
    """
    module_name = get_module_name(spec_path)
    
    # Check if the sanity check passes
    if not run_sanity_check(spec_path):
        logging.error("Sanity check failed. Cannot compile.")
        return False
    
    # Get the code target
    code_target = get_code_target(spec_path)
    if not code_target:
        logging.info(f"No code target for {spec_path}. Nothing to compile.")
        return True
    
    # Paths to the preprocessed spec and Q&A
    no_context_spec_path = Path(f"tlc/{module_name}.no-context.md")
    q_and_a_path = Path(f"tlc/{module_name}.questions.md")
    
    # Read the preprocessed spec
    with open(no_context_spec_path, "r") as f:
        no_context_spec = f.read()
    
    # Read the Q&A if it exists
    q_and_a = ""
    if q_and_a_path.exists():
        with open(q_and_a_path, "r") as f:
            q_and_a = f.read()
    
    # Create the output directory if it doesn't exist
    output_dir = Path(os.path.dirname(f"tlc/{code_target}"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a chat instance with the system prompt
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
    
    chat = SimpleChat(system_prompt, model="claude-sonnet")
    
    # Generate the code
    logging.info(f"Generating code for {code_target}")
    prompt_template = """
    Consider the following specification:

    ====== BEGIN {{ module_name }} specification ======
    {{ no_context_spec }}
    ====== END {{ module_name }} specification ======

    We have reviewed this specification, and discussed some clarifications in this Q&A:

    {{ q_and_a }}

    The specification is ready to implement in {{ module_code_target }}. Write the code for this module. Do not write anything else, just the code.
    """
    
    code = chat.call(
        prompt_template,
        module_name=module_name,
        no_context_spec=no_context_spec,
        q_and_a=q_and_a,
        module_code_target=code_target
    )
    
    # Save the generated code
    with open(f"tlc/{code_target}", "w") as f:
        f.write(code)
    logging.info(f"Saved generated code to tlc/{code_target}")
    
    # Review the code
    logging.info("Reviewing the generated code")
    prompt_template = """
    Consider the following specification:

    ====== BEGIN {{ module_name }} specification ======
    {{ no_context_spec }}
    ====== END {{ module_name }} specification ======

    Here is our implementation:

    ====== BEGIN {{ module_code_target }} implementation ======
    {{ code }}
    ====== END {{ module_code_target }} implementation ======

    Review this implementation. Is it complete? Is it valid code? Does it meet our specifications expectations?
    """
    
    review = chat.call(
        prompt_template,
        module_name=module_name,
        no_context_spec=no_context_spec,
        module_code_target=code_target,
        code=code
    )
    logging.debug(f"Code review:\n{review}")
    
    # Check if the implementation is ready
    prompt_template = """
    Answering only yes or no, is this implementation ready to use?
    """
    
    ready_response = chat.call(prompt_template)
    is_ready = ready_response.lower().strip() == "yes"
    
    if is_ready:
        logging.info("Compile succeeded")
        return True
    else:
        # Get suggestions for improvement
        prompt_template = """
        Summarise why this implementation is not ready. Briefly give some suggestions as to how we might improve the specification to fix this.
        """
        
        suggestions = chat.call(prompt_template)
        logging.error(f"Compile failed. Suggestions for improvement:\n{suggestions}")
        return False

def main():
    """Main entry point for the compile tool."""
    parser = argparse.ArgumentParser(description="Compile a specification document into code")
    parser.add_argument("spec_path", help="Path to the specification document")
    args = parser.parse_args()
    
    # Get the module name for logging
    module_name = get_module_name(args.spec_path)
    
    # Set up logging
    setup_logging(module_name)
    
    try:
        # Compile the specification
        success = compile_spec(args.spec_path)
        
        # Exit with appropriate status code
        sys.exit(0 if success else 1)
    except Exception as e:
        logging.error(f"Error during compilation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 