"""
Specification Document Parser

This module provides functionality to parse and analyze specification documents
written in markdown format. It can extract imports, describe interfaces, and
handle dependencies between specification documents.
"""

import os
import re
from typing import List, Optional, Set

from tlc.markdown_parser import parse_markdown, Block, TextBlock, CodeBlock, Section
from tlc.llm.simple_chat_chain import SimpleChat

def load_specification_document(path: str) -> Section:
    """
    Parse a markdown specification document into a Section object.
    
    Args:
        path: Path to the markdown specification document
        
    Returns:
        A Section object representing the parsed document
    """
    blocks = parse_markdown(path)
    
    # The first block should be a section with the title of the document
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Expected first block of {path} to be a Section, got {type(blocks[0])}")
    
    return blocks[0]

def list_imports(spec: Section) -> List[str]:
    """
    List all imports/dependencies from a specification document.
    
    Args:
        spec: A Section object representing a parsed specification document
        
    Returns:
        A list of import paths
    """
    imports = []
    
    # Create a system prompt for Claude to extract imports
    system_prompt = """
    You are an assistant that identifies dependencies in markdown specification documents.
    Look for dependencies marked with @ symbol, like @path/to/file.md.
    Only list actual dependencies, one per line, without the @ symbol.
    Do not include any explanations or other text.
    """
    
    # Process each block to find imports
    for block in _flatten_blocks(spec):
        if isinstance(block, TextBlock) or isinstance(block, CodeBlock):
            content = block.text if isinstance(block, TextBlock) else block.code
            
            # First try to extract imports using regex
            pattern = r'@([a-zA-Z0-9_\-./]+\.md)'
            regex_imports = re.findall(pattern, content)
            
            if regex_imports:
                imports.extend(regex_imports)
            else:
                # If regex doesn't find anything, use LLM as a fallback
                chat = SimpleChat(system_prompt, model="claude-haiku")
                llm_response = chat.call("Identify dependencies in this text:\n\n{{content}}", content=content)
                
                # Process the LLM response - each line should be a dependency
                for line in llm_response.strip().split('\n'):
                    if line.strip() and not line.startswith('@'):
                        imports.append(line.strip())
    
    # Remove duplicates while preserving order
    unique_imports = []
    for imp in imports:
        if imp not in unique_imports:
            unique_imports.append(imp)
    
    return unique_imports

def describe_interface(spec: Section) -> Section:
    """
    Create a new Section that only contains blocks describing the interface.
    Also includes interfaces of dependencies needed to understand this interface.
    
    Args:
        spec: A Section object representing a parsed specification document
        
    Returns:
        A Section object containing only interface-related blocks and required dependencies
    """
    # Create a system prompt for Claude to identify interface blocks
    system_prompt = """
    You are an assistant that identifies blocks in markdown specification documents
    that describe the interface or usage instructions for a module.
    
    For each block, determine if it describes:
    1. How to use the module
    2. The public API/interface of the module
    3. Examples of using the module
    
    Answer with only "yes" or "no".
    """
    
    interface_blocks = []
    processed_dependencies = set()
    
    # Create a new section with the same title
    interface_section = Section(spec.title, [])
    
    # Find blocks that describe the interface
    for block in spec.children:
        if isinstance(block, Section):
            # Check if this section describes the interface
            chat = SimpleChat(system_prompt, model="claude-haiku")
            is_interface = chat.call(
                "Does the section titled '{{title}}' likely describe the interface or usage of a module?\n\n",
                title=block.title
            ).lower().strip()
            
            if "yes" in is_interface:
                interface_blocks.append(block)
    
    # Add the interface blocks to the new section
    interface_section.children = interface_blocks
    
    # Get dependencies required to understand this interface
    interface_imports = list_imports(interface_section)
    
    # Load dependencies recursively
    for import_path in interface_imports:
        if import_path in processed_dependencies:
            continue
        
        processed_dependencies.add(import_path)
        
        try:
            # Resolve the path relative to the current directory
            dependency_path = import_path
            if not os.path.isabs(dependency_path):
                # Try to find the dependency in common locations
                possible_paths = [
                    import_path,
                    os.path.join("the-last-compiler", import_path),
                    os.path.join("the-last-compiler", "llm", import_path.replace("llm/", "")),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        dependency_path = path
                        break
            
            # Load and process the dependency
            dependency_spec = load_specification_document(dependency_path)
            dependency_interface = describe_interface(dependency_spec)
            
            # Prepend the dependency interface to our interface section
            dependency_section = Section(
                f"Dependency: {import_path}",
                dependency_interface.children
            )
            interface_section.children.insert(0, dependency_section)
            
        except Exception as e:
            # If we can't load a dependency, add a note about it
            error_block = TextBlock(f"Error loading dependency {import_path}: {str(e)}")
            interface_section.children.insert(0, error_block)
    
    return interface_section

def _flatten_blocks(section: Section) -> List[Block]:
    """
    Recursively flatten a section and its children into a list of blocks.
    
    Args:
        section: A Section object to flatten
        
    Returns:
        A flat list of all blocks in the section and its children
    """
    blocks = [section]
    
    for child in section.children:
        if isinstance(child, Section):
            blocks.extend(_flatten_blocks(child))
        else:
            blocks.append(child)
    
    return blocks 