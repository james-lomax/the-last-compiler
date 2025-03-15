import os
import sys
import re
from typing import List, Optional, Set
from pathlib import Path

from tlc.markdown_parser import parse_markdown, render_markdown, Block, Section, TextBlock, CodeBlock
from tlc.llm.simple_chat_chain import SimpleChat
from tlc.llm.langchain_logging import log_chat, save_logs

def load_specification_document(spec_path: str) -> Section:
    """
    Load a specification document from a file.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        The root section of the document
    """
    blocks = parse_markdown(spec_path)
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Invalid specification document: {spec_path}")
    
    return blocks[0]

def list_imports(spec_path: str) -> List[str]:
    """
    List imports for the whole file by parsing each text block and asking the LLM to identify dependencies.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        List of dependencies as strings
    """
    try:
        root_section = load_specification_document(spec_path)
        imports = []
        
        # First try to extract imports using regex
        for block in root_section.children:
            if isinstance(block, TextBlock):
                # Look for [[path/to/file]] patterns
                matches = re.findall(r'\[\[([^\s\n]+)\]\]', block.text)
                if matches:
                    imports.extend(matches)
                else:
                    # If regex doesn't find anything, use LLM
                    block_imports = _list_imports_for_block(block.text)
                    imports.extend(block_imports)
        
        # Remove duplicates while preserving order
        unique_imports = []
        for imp in imports:
            if imp not in unique_imports:
                unique_imports.append(imp)
        
        return unique_imports
    except Exception as e:
        print(f"Error listing imports for {spec_path}: {e}")
        raise

def _list_imports_for_block(text: str) -> List[str]:
    """
    Ask the LLM to identify imports in a text block.
    
    Args:
        text: The text content to analyze
        
    Returns:
        List of dependencies found in the text
    """
    system_prompt = """
    You are an assistant that identifies dependencies in markdown specification documents.
    Dependencies are indicated by '[[path/to/file]]' syntax in the text.
    Your task is to extract these dependencies and list them one per line.
    Only return the dependencies, without any additional text - strip the `[[` and `]]` from the dependencies.
    If there are no dependencies, respond with "no dependencies".
    """
    
    try:
        chat = SimpleChat(system_prompt, model="claude-haiku")
        response = chat.call("Identify all dependencies in the following text:\n\n{{text}}", text=text)
        
        # Process the response
        if "no dependencies" in response.lower():
            return []
        
        # Extract dependencies from the response
        dependencies = []
        for line in response.strip().split('\n'):
            line = line.strip()
            dependencies.append(line)
        
        return dependencies
    except Exception as e:
        print(f"Error identifying imports in block: {e}")
        return []

def describe_interface(spec_path: str, processed_deps: Optional[Set[str]] = None) -> Section:
    """
    Find blocks that describe the interface of the module and create a Section with those blocks.
    Also includes interfaces from dependencies.
    
    Args:
        spec_path: Path to the specification document
        processed_deps: Set of already processed dependencies to avoid cycles
        
    Returns:
        Section block with interface description
    """
    if processed_deps is None:
        processed_deps = set()
        
    try:
        root_section = load_specification_document(spec_path)
        interface_blocks = []
        
        # Include top-level TextBlocks
        for block in root_section.children:
            if isinstance(block, TextBlock):
                interface_blocks.append(block)
        
        # Process second-level sections to find interface descriptions
        for block in root_section.children:
            if isinstance(block, Section):
                if _is_interface_section(block.title, block):
                    interface_blocks.append(block)
        
        # Create a new section with the interface blocks
        interface_section = Section(title=root_section.title, children=interface_blocks)
        
        # Get dependencies required to understand this interface
        dependencies = list_imports(spec_path)
        
        # Process dependencies
        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        for dep in dependencies:
            if dep in processed_deps:
                continue
                
            dep_path = os.path.join(spec_dir, dep)
            try:
                if not os.path.exists(dep_path):
                    raise FileNotFoundError(f"Dependency not found: {dep_path}")
                
                # Add to processed deps to avoid cycles
                processed_deps.add(dep)
                
                # Get the interface of the dependency
                dep_interface = describe_interface(dep_path, processed_deps)
                
                # Prepend the dependency interface to our interface section
                interface_section.children = dep_interface.children + interface_section.children
            except FileNotFoundError as e:
                print(f"Error: {e}")
                raise
            except Exception as e:
                print(f"Error processing dependency {dep}: {e}")
                raise
        
        return interface_section
    except Exception as e:
        print(f"Error describing interface for {spec_path}: {e}")
        raise

def _is_interface_section(title: str, section: Section) -> bool:
    """
    Ask the LLM if a section describes the interface or usage of the module.
    
    Args:
        title: The title of the section
        section: The section to analyze
        
    Returns:
        True if the section describes the interface, False otherwise
    """
    # Common titles that typically describe interfaces
    interface_titles = ["interface", "usage", "api", "public api", "functions", "methods"]
    
    # Check if the title is a common interface title
    if title.lower() in interface_titles:
        return True
    
    system_prompt = """
    You are an assistant that analyzes markdown sections to determine if they describe 
    the interface or usage instructions of a module.
    
    Your task is to determine if the given section with the provided title is likely 
    describing the interface or usage instructions for the module by other Python modules.
    
    Respond with only "yes" or "no".
    """
    
    # Convert the section to text for analysis
    section_text = render_markdown([section])
    
    try:
        chat = SimpleChat(system_prompt, model="claude-haiku")
        prompt = f"Does the following section titled '{title}' describe the interface or usage instructions of a module?\n\n{section_text}"
        response = chat.call(prompt)
        
        return response.lower().strip() == "yes"
    except Exception as e:
        print(f"Error determining if section is an interface: {e}")
        # Default to including the section if there's an error
        return True

def preprocess_spec_context(spec_path: str) -> str:
    """
    Preprocess a specification document by extracting interfaces and prepending them.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        Modified markdown document as a string
    """
    try:
        # Get the interface description
        interface_section = describe_interface(spec_path)
        
        # Load the original specification
        root_section = load_specification_document(spec_path)
        
        # Render the interface and the original spec
        interface_md = render_markdown([interface_section])
        original_md = render_markdown([root_section])
        
        return interface_md
    except Exception as e:
        print(f"Error preprocessing spec context for {spec_path}: {e}")
        raise

def main():
    """CLI entry point for the module."""
    try:
        if len(sys.argv) < 3:
            print("Usage: python -m tlc.specification_document preprocess <spec-path>")
            sys.exit(1)
        
        command = sys.argv[1]
        spec_path = sys.argv[2]
        
        if command == "preprocess":
            result = preprocess_spec_context(spec_path)
            print(result)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: preprocess")
            sys.exit(1)
    finally:
        save_logs()

if __name__ == "__main__":
    main() 