#!/usr/bin/env python3
"""
This module provides utilities for pre-processing specification documents to be used by the compiler.
"""

import os
import re
import sys
import argparse
from typing import List, Optional, Set

from tlc.markdown_parser import parse_markdown, render_markdown, TextBlock, Section, Block


def list_import_for_block(block: TextBlock) -> List[str]:
    """
    Checks if there are any strings in the block match `\[\[([a-zA-Z\d \-\/]+)\]\]` and extracts the dependency name.
    
    Args:
        block: The TextBlock to check for dependencies
        
    Returns:
        A list of dependency file names with extensions
    """
    if not isinstance(block, TextBlock):
        return []
    
    # Find all matches of the pattern [[file]] or [[path/to/file]]
    pattern = r'\[\[([a-zA-Z\d \-\/]+)\]\]'
    matches = re.findall(pattern, block.text)
    
    # Add .md extension if no extension is present
    result = []
    for match in matches:
        if '.' not in match.split('/')[-1]:
            result.append(f"{match}.md")
        else:
            result.append(match)
    
    return result


def get_public_interface_blocks(spec_path: str) -> Section:
    """
    Reads the spec file and extracts blocks describing the public interface.
    
    Args:
        spec_path: Path to the specification file
        
    Returns:
        A Section containing the public interface blocks
    """
    blocks = parse_markdown(spec_path)
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Invalid specification file format: {spec_path}")
    
    root_section = blocks[0]
    interface_section = Section(title=f"Interface from {os.path.basename(spec_path)}", children=[])
    
    # Include any top-level TextBlocks
    for child in root_section.children:
        if isinstance(child, TextBlock):
            interface_section.children.append(child)
    
    # Check for second-level blocks that describe interfaces
    for child in root_section.children:
        if isinstance(child, Section):
            title_lower = child.title.lower()
            if any(keyword in title_lower for keyword in ["interface", "usage", "api", "public", "exported"]):
                interface_section.children.append(child)
    
    return interface_section


def describe_dependency_interfaces(spec_path: str) -> Section:
    """
    Describes all the interfaces needed to implement this module.
    
    Args:
        spec_path: Path to the specification file
        
    Returns:
        A Section containing all dependency interfaces
    """
    # Create the root section for all dependencies
    dependencies_section = Section(title="Dependencies", children=[])
    
    # Get the base directory of the spec file for relative imports
    base_dir = os.path.dirname(os.path.abspath(spec_path))
    
    # Parse the main spec file
    blocks = parse_markdown(spec_path)
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Invalid specification file format: {spec_path}")
    
    root_section = blocks[0]
    
    # Initialize the set of dependencies to visit
    dependencies_to_visit = set()
    visited_dependencies = set()
    
    # Collect initial dependencies from the main spec file
    for child in root_section.children:
        if isinstance(child, TextBlock):
            for dep in list_import_for_block(child):
                dependencies_to_visit.add(dep)
        elif isinstance(child, Section):
            for grandchild in child.children:
                if isinstance(grandchild, TextBlock):
                    for dep in list_import_for_block(grandchild):
                        dependencies_to_visit.add(dep)
    
    # Process dependencies until we've visited all of them
    while dependencies_to_visit:
        dep = dependencies_to_visit.pop()
        visited_dependencies.add(dep)
        
        # Resolve the dependency path
        dep_path = _resolve_dependency_path(dep, base_dir)
        if not dep_path:
            raise FileNotFoundError(f"Dependency not found: {dep}")
        
        try:
            # Get the interface blocks from this dependency
            interface_section = get_public_interface_blocks(dep_path)
            dependencies_section.children.append(interface_section)
            
            # Find new dependencies in this dependency
            dep_blocks = parse_markdown(dep_path)
            if dep_blocks and isinstance(dep_blocks[0], Section):
                dep_root = dep_blocks[0]
                _collect_dependencies_from_section(dep_root, dependencies_to_visit, visited_dependencies)
                
        except Exception as e:
            raise Exception(f"Error processing dependency {dep}: {str(e)}") from e
    
    return dependencies_section


def _resolve_dependency_path(dep: str, base_dir: str) -> Optional[str]:
    """
    Resolves a dependency path relative to the base directory.
    
    Args:
        dep: The dependency path
        base_dir: The base directory to resolve from
        
    Returns:
        The resolved path or None if not found
    """
    # Try direct path resolution
    direct_path = os.path.join(base_dir, dep)
    if os.path.exists(direct_path):
        return direct_path
    
    # Try searching in subdirectories
    for root, _, files in os.walk(base_dir):
        if os.path.basename(dep) in files:
            return os.path.join(root, os.path.basename(dep))
    
    return None


def _collect_dependencies_from_section(section: Section, to_visit: Set[str], visited: Set[str]) -> None:
    """
    Collects dependencies from a section and adds them to the to_visit set if not already visited.
    
    Args:
        section: The section to collect dependencies from
        to_visit: Set of dependencies to visit
        visited: Set of already visited dependencies
    """
    for child in section.children:
        if isinstance(child, TextBlock):
            for dep in list_import_for_block(child):
                if dep not in visited:
                    to_visit.add(dep)
        elif isinstance(child, Section):
            _collect_dependencies_from_section(child, to_visit, visited)


def preprocess_spec_context(path: str) -> str:
    """
    Preprocesses a specification document by adding dependency interfaces.
    
    Args:
        path: Path to the specification file
        
    Returns:
        A modified markdown document with dependency interfaces prepended
    """
    try:
        # Parse the original spec file
        blocks = parse_markdown(path)
        if not blocks or not isinstance(blocks[0], Section):
            raise ValueError(f"Invalid specification file format: {path}")
        
        # Get dependency interfaces
        dependencies_section = describe_dependency_interfaces(path)
        
        # Create a new root section with dependencies first, then original content
        root_section = blocks[0]
        new_root = Section(title=root_section.title, children=[dependencies_section] + root_section.children)
        
        # Render the modified document
        return render_markdown([new_root])
        
    except Exception as e:
        print(f"Error preprocessing spec context: {str(e)}", file=sys.stderr)
        raise


def get_code_target(path: str) -> Optional[str]:
    """
    Returns the name of the python module this specification describes.
    
    Args:
        path: Path to the specification file
        
    Returns:
        The module name or None if it's documentation only
    """
    blocks = parse_markdown(path)
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Invalid specification file format: {path}")
    
    root_section = blocks[0]
    module_name = root_section.title.strip()
    
    if module_name.endswith('.py'):
        return module_name
    elif module_name.endswith('.md'):
        return None
    else:
        raise ValueError(f"Invalid module name: {module_name}. Must end with .py or .md")


def main():
    """CLI entry point for the module."""
    parser = argparse.ArgumentParser(description="Preprocess specification documents")
    parser.add_argument("command", choices=["preprocess"], help="Command to execute")
    parser.add_argument("spec_path", help="Path to the specification document")
    
    args = parser.parse_args()
    
    if args.command == "preprocess":
        try:
            result = preprocess_spec_context(args.spec_path)
            print(result)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main() 