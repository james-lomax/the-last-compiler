"""
Specification document parser and interface extractor.

This module provides functionality to parse specification documents,
extract their interfaces, and handle dependencies between specifications.
"""

import os
import re
from typing import List, Set

from tlc.markdown_parser import parse_markdown, Section, TextBlock, CodeBlock, Block
from tlc.llm.simple_chat_chain import SimpleChat

def load_specification_document(spec_path: str) -> Section:
    """
    Load a specification document from a file.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        Section: The root section of the specification document
        
    Raises:
        FileNotFoundError: If the specification file doesn't exist
        ValueError: If the specification doesn't contain a valid section
    """
    # Check if the file exists
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"Specification document not found: {spec_path}")
    
    # Parse the markdown file
    blocks = parse_markdown(spec_path)
    
    # Validate the result
    if not blocks:
        raise ValueError(f"Specification document {spec_path} is empty")
    
    if not isinstance(blocks[0], Section):
        raise ValueError(f"Specification document {spec_path} does not start with a section")
    
    # Set the title to the file path if it's not already set
    # This helps with debugging and error messages
    if not blocks[0].title:
        blocks[0].title = os.path.basename(spec_path)
    
    return blocks[0]

def list_imports(spec: Section) -> List[str]:
    """
    List all imports/dependencies in a specification document.
    
    Args:
        spec: The specification document section
        
    Returns:
        List[str]: List of import paths
    """
    imports = set()
    
    # First try to extract imports using regex
    for block in _flatten_blocks(spec):
        if isinstance(block, TextBlock):
            # Find all @path/to/file.md patterns
            matches = re.findall(r'@([^\s\n]+\.md)', block.text)
            imports.update(matches)
        elif isinstance(block, CodeBlock):
            # Also check code blocks for imports
            matches = re.findall(r'@([^\s\n]+\.md)', block.code)
            imports.update(matches)
    
    # If no imports found with regex, use LLM to extract them
    if not imports:
        chat = SimpleChat(
            system_prompt="""
            You are a dependency analyzer for specification documents.
            Your task is to identify dependencies marked with @ symbol (like @path/to/file.md).
            Return only the dependencies, one per line, without any other text.
            If you can't find any dependencies, return "no dependencies".
            """,
            model="claude-haiku"
        )
        
        # Convert the spec to markdown text for the LLM
        spec_text = ""
        for block in _flatten_blocks(spec):
            if isinstance(block, TextBlock):
                spec_text += block.text + "\n\n"
            elif isinstance(block, CodeBlock):
                spec_text += f"```{block.language}\n{block.code}\n```\n\n"
        
        # Ask the LLM to find dependencies
        llm_response = chat.call("Please identify all dependencies in this specification:\n\n{{spec_text}}", spec_text=spec_text)
        
        # Parse the LLM response
        if llm_response.strip():
            for line in llm_response.strip().split("\n"):
                if line.strip() and "no dependencies" not in line.lower():
                    imports.add(line.strip())
    
    return list(imports)

def describe_interface(spec: Section, spec_path: str = None) -> Section:
    """
    Extract the interface description from a specification document.
    
    Args:
        spec: The specification document section
        spec_path: Path to the specification document (for resolving relative imports)
        
    Returns:
        Section: A new section containing only the interface-related blocks
    """
    # Create a new section with the same title
    interface_section = Section(spec.title, [])
    
    # Find blocks that describe the interface
    chat = SimpleChat(
        system_prompt="""
        You are an interface analyzer for specification documents.
        Your task is to determine if a section describes the interface or usage instructions.
        Interface sections typically have titles like "Interface", "Usage", "API", or "Examples".
        Answer with only 'yes' or 'no'.
        """,
        model="claude-haiku"
    )
    
    # Check each second-level section
    interface_blocks = []
    for child in spec.children:
        if isinstance(child, Section):
            # Some section titles are clearly interface-related without needing to ask the LLM
            if child.title.lower() in ["interface", "usage", "api", "examples"]:
                interface_blocks.append(child)
                continue
                
            # Ask the LLM if this section describes the interface
            is_interface = chat.call(
                "Does the section titled '{{title}}' describe the interface or usage instructions for a module? Answer with only 'yes' or 'no'.",
                title=child.title
            ).strip().lower()
            
            if is_interface == "yes":
                interface_blocks.append(child)
    
    # Add the interface blocks to our section
    interface_section.children = interface_blocks
    
    # If we didn't find any interface blocks, add a note
    if not interface_blocks:
        interface_section.children.append(TextBlock("No interface description found in this specification."))
    
    # Get dependencies required to understand this interface
    dependencies = list_imports(interface_section)
    loaded_dependencies = set()
    
    # Process dependencies
    for dependency in dependencies:
        if dependency in loaded_dependencies:
            continue
        
        # Resolve the dependency path relative to the spec's directory
        if spec_path and not os.path.isabs(dependency):
            spec_dir = os.path.dirname(os.path.abspath(spec_path))
            dependency_path = os.path.join(spec_dir, dependency)
        else:
            dependency_path = dependency
        
        # Check if the dependency exists
        if not os.path.exists(dependency_path):
            error_message = f"Dependency {dependency} not found at {dependency_path}"
            print(error_message)
            raise FileNotFoundError(error_message)
        
        try:
            # Load the dependency
            dependency_spec = load_specification_document(dependency_path)
            
            # Get the interface of the dependency
            dependency_interface = describe_interface(dependency_spec, dependency_path)
            
            # Create a section for the dependency
            dependency_section = Section(f"Dependency: {dependency}", dependency_interface.children)
            
            # Add the dependency interface to the beginning of our interface
            interface_section.children.insert(0, dependency_section)
            
            # Mark this dependency as loaded
            loaded_dependencies.add(dependency)
        except Exception as e:
            error_message = f"Error loading dependency {dependency}: {str(e)}"
            print(error_message)
            raise
    
    return interface_section

def preprocess_spec_context(spec_path: str) -> str:
    """
    Preprocess a specification document by adding interface descriptions of dependencies.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        str: Modified markdown document with interfaces prepended
    """
    try:
        # Load the specification document
        spec = load_specification_document(spec_path)
        
        # Get the interface description
        interface = describe_interface(spec, spec_path)
        
        # Convert the interface to markdown
        from tlc.markdown_parser import render_markdown
        
        # Read the original document content
        with open(spec_path, 'r') as f:
            original_content = f.read()
        
        # Render the interface description
        interface_content = render_markdown([interface])
        
        # Combine the interface description with the original content
        # Add a separator between the interface and the original content
        return interface_content + "\n\n---\n\n" + original_content
    except Exception as e:
        raise Exception(f"Error preprocessing specification {spec_path}: {str(e)}") from e

def _flatten_blocks(section: Section) -> List[Block]:
    """
    Flatten a section hierarchy into a list of blocks.
    
    Args:
        section: The section to flatten
        
    Returns:
        List[Block]: Flattened list of blocks
    """
    blocks = []
    
    for child in section.children:
        if isinstance(child, Section):
            blocks.append(child)  # Add the section itself
            blocks.extend(_flatten_blocks(child))  # Add its children
        else:
            blocks.append(child)
    
    return blocks

def load_and_describe_interface(spec_path: str) -> Section:
    """
    Load a specification document and describe its interface.
    
    This is a convenience function that combines loading a specification document
    and describing its interface in one step.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        Section: A section containing only the interface-related blocks
        
    Raises:
        FileNotFoundError: If the specification file or any of its dependencies don't exist
        Exception: If there's an error loading the specification or any of its dependencies
    """
    try:
        spec = load_specification_document(spec_path)
        return describe_interface(spec, spec_path)
    except Exception as e:
        print(f"Error loading and describing interface for {spec_path}: {str(e)}")
        raise 