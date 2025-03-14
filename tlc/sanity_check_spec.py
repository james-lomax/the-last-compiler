import os
import sys
import logging
from pathlib import Path
from typing import Optional
from .simple_chat_chain import SimpleChat

# Configure logging
def setup_logging(module_name: str) -> None:
    """Setup logging configuration for both file and console output."""
    # Create logs directory if it doesn't exist
    log_dir = Path("slop/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Console handler - only INFO and above, message only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)
    
    # File handler - DEBUG and above, with all details
    file_handler = logging.FileHandler(log_dir / f"{module_name}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(file_handler)

def read_spec_file(spec_path: str) -> str:
    """Read the specification file contents."""
    with open(spec_path, 'r') as f:
        return f.read()

def read_qa_file(module_name: str) -> Optional[str]:
    """Read the Q&A file if it exists."""
    qa_path = Path("slop") / f"{module_name}.questions.md"
    if qa_path.exists():
        with open(qa_path, 'r') as f:
            return f.read()
    return None

def write_qa_file(module_name: str, content: str) -> None:
    """Write the Q&A file."""
    qa_dir = Path("slop")
    qa_dir.mkdir(exist_ok=True)
    qa_path = qa_dir / f"{module_name}.questions.md"
    
    with open(qa_path, 'w') as f:
        f.write(content)
    
    logging.info(f"Updated {qa_path}")

def main() -> None:
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: sanity-check-spec module-name.md")
        sys.exit(1)
    
    # Get module name and setup logging
    spec_path = sys.argv[1]
    if not spec_path.endswith('.md'):
        print("Error: Specification file must be a markdown file")
        sys.exit(1)
    
    module_name = spec_path[:-3]  # Remove .md extension
    setup_logging(module_name)
    
    try:
        # Read the spec and Q&A files
        logging.info(f"Reading specification from {spec_path}")
        spec_content = read_spec_file(spec_path)
        qa_content = read_qa_file(module_name)
        
        # Initialize chat with system prompt
        system_prompt = """You are a specification compiler. You take markdown documents describing the implementation of a single python module file and turn them into code.

The specification files should generally define:
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented."""
        
        chat = SimpleChat(system_prompt)
        logging.info("Starting specification analysis")
        
        # Initial sanity check
        logging.debug("Performing initial sanity check")
        chat.call("""Read the spec

{{ spec }}

Is it ambiguous? Are there problems that the spec doesn't address? Are there unanswered questions?""",
            spec=spec_content
        )
        
        # Check if we have enough information
        logging.debug("Checking if specification is complete")
        explanation = chat.call(
            """{% if q_and_a %}
Here is a Q&A from our last review of this document:

{{ q_and_a }}{% endif %}

Do we have enough information to implement this specification in code? Does this implementation make sense? Will it work? Why not?

We are allowed to make reasonable assumptions, but we must explain them.""",
            q_and_a=qa_content
        )
        logging.info(explanation)
        
        # Should we build?
        logging.debug("Checking if we should proceed with build")
        build_response = chat.call(
            "In summary, should we build this, or do we need to improve the spec? Just answer yes or no, nothing else."
        )
        build_failed = build_response.lower().strip() == "no"
        
        # Check for questions
        logging.debug("Checking for unanswered questions")
        questions_response = chat.call(
            "Are there unanswered questions? Just answer yes or no, nothing else."
        )
        has_questions = questions_response.lower().strip() == "yes"
        
        # Generate Q&A if needed
        if has_questions:
            logging.info("Generating Q&A file")
            qa_content = chat.call(
                """List all the unanswered questions or clarifications, and besides each one, write your best assumption on the answer.

Do not number the questions, just list them like this:

**Question**: {question}
  **Assumption**: {assumption}

If there is an **Answer** from the last review, you must keep it the same."""
            )
            write_qa_file(module_name, qa_content)
        
        # Final status
        if build_failed:
            logging.info("Specification needs improvement before implementation")
            sys.exit(1)
        else:
            logging.info("Specification is ready for implementation")
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Error processing specification: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 