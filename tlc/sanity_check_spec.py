import os
import sys
import logging
import argparse
from pathlib import Path
import jinja2

from tlc.llm.simple_chat_chain import SimpleChat
from tlc.specification_document import preprocess_spec_context, get_code_target

def setup_logging(module_name):
    """
    Set up logging for the sanity check process.
    
    Args:
        module_name: The name of the module being checked
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("tlc/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up file handler
    log_file = log_dir / f"{module_name}.log"
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

def sanity_check_spec(spec_path, q_and_a_path=None):
    """
    Perform a sanity check on the specification document.
    
    Args:
        spec_path: Path to the specification document
        q_and_a_path: Optional path to an existing Q&A file
        
    Returns:
        A tuple of (build_failed, has_questions, q_and_a_content)
    """
    logging.info(f"Sanity checking specification: {spec_path}")
    
    # Preprocess the spec to be context-free
    logging.info("Preprocessing specification to be context-free")
    no_context_spec = preprocess_spec_context(spec_path)
    
    # Check if this document is intended to produce code
    code_target = get_code_target(spec_path)
    if code_target is None:
        logging.info(f"No need to compile {spec_path} as it contains no code target")
        return False, False, None
    
    # Save the preprocessed spec
    module_name = get_module_name(spec_path)
    no_context_path = Path(f"tlc/{module_name}.no-context.md")
    with open(no_context_path, "w") as f:
        f.write(no_context_spec)
    logging.info(f"Saved context-free spec to {no_context_path}")
    
    # Load existing Q&A if available
    q_and_a_content = None
    if q_and_a_path and os.path.exists(q_and_a_path):
        with open(q_and_a_path, "r") as f:
            q_and_a_content = f.read()
        logging.info(f"Loaded existing Q&A from {q_and_a_path}")
    
    # Create a chat instance with the system prompt
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
    
    chat = SimpleChat(system_prompt, debug_name=f"{spec_path}.sanity-check", model="claude-sonnet")
    
    # First prompt: Initial sanity check
    logging.info("Performing initial sanity check")
    prompt_template = """
    Read the spec

    {{ spec }}

    Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions? Are there references to concepts that are not yet defined and understood?
    """
    
    response = chat.call(prompt_template, spec=no_context_spec)
    logging.debug(f"Initial sanity check response:\n{response}")
    
    # Second prompt: Evaluate if we have enough information
    logging.info("Evaluating if we have enough information")
    prompt_template = """
    {% if q_and_a %}
    Here is a Q&A from our last review of this document:

    {{ q_and_a }}{% endif %}

    Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

    We are allowed to make reasonable assumptions, but we must explain them.
    """
    
    explanation = chat.call(prompt_template, q_and_a=q_and_a_content)
    logging.debug(f"Evaluation response:\n{explanation}")
    
    # Third prompt: Should we build this?
    logging.info("Determining if we should build this")
    prompt_template = """
    In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else.
    """
    
    build_response = chat.call(prompt_template)
    build_failed = build_response.lower().strip() == "no"
    logging.debug(f"Build decision: {'No' if build_failed else 'Yes'}")
    
    # Fourth prompt: Are there unanswered questions?
    logging.info("Checking for unanswered questions")
    prompt_template = """
    Are there unanswered questions? Just answer yes or no, nothing else.
    """
    
    questions_response = chat.call(prompt_template)
    has_questions = questions_response.lower().strip() == "yes"
    logging.debug(f"Has questions: {'Yes' if has_questions else 'No'}")
    
    # If there are questions, generate Q&A
    q_and_a_content_updated = None
    if has_questions:
        logging.info("Generating Q&A")
        prompt_template = """
        List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

        Do not number the questions, just list them like this:

        **Question**: {{ "{question}" }}
          **Assumption**: {{ "{assumption}" }}

        If there is an **Answer** from the last review, you must keep it the same.

        If there is no reasonable way to answer the question, do not make an assumption, just state that you don't know. If you're unsure about a particular assumption, say so.
        """
        
        q_and_a_content_updated = chat.call(prompt_template)
        logging.debug(f"Generated Q&A:\n{q_and_a_content_updated}")
    
    # If build failed, ask for critical questions
    critical_questions = None
    if build_failed:
        logging.info("Identifying critical questions")
        prompt_template = """
        Which questions are critical to answer in order to build this module?
        """
        
        critical_questions = chat.call(prompt_template)
        logging.debug(f"Critical questions:\n{critical_questions}")
    
    return build_failed, has_questions, q_and_a_content_updated, critical_questions

def main():
    """Main entry point for the sanity check tool."""
    parser = argparse.ArgumentParser(description="Sanity check a specification document")
    parser.add_argument("spec_path", help="Path to the specification document")
    args = parser.parse_args()
    
    # Get the module name for logging
    module_name = get_module_name(args.spec_path)
    
    # Set up logging
    setup_logging(module_name)
    
    try:
        # Path to the Q&A file
        q_and_a_path = Path(f"tlc/{module_name}.questions.md")
        
        # Perform the sanity check
        build_failed, has_questions, q_and_a_content, critical_questions = sanity_check_spec(args.spec_path, q_and_a_path)
        
        # Save the Q&A if there are questions
        if has_questions and q_and_a_content:
            with open(q_and_a_path, "w") as f:
                f.write(q_and_a_content)
            logging.info(f"Saved Q&A to {q_and_a_path}")
        
        # Report the result
        if build_failed:
            logging.info("Sanity check failed. The specification needs improvement.")
            if critical_questions:
                logging.info("Critical questions to answer:")
                logging.info(critical_questions)
            sys.exit(1)
        else:
            logging.info("Sanity check passed. The specification is ready to be compiled.")
            sys.exit(0)
    except Exception as e:
        logging.error(f"Error during sanity check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 