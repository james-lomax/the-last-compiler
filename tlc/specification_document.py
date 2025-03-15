import os
import re
from typing import List, Optional
from pathlib import Path

from tlc.markdown_parser import parse_markdown, Block, TextBlock, CodeBlock, Section
from tlc.llm.simple_chat_chain import SimpleChat

def list_imports(spec_path: str) -> List[str]:
    """
    List all imports referenced in the specification document.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        A list of import paths
    """
    blocks = parse_markdown(spec_path)
    imports = []
    
    # Process each block to find imports
    for block in blocks:
        if isinstance(block, Section):
            # Recursively process sections
            for child in block.children:
                if isinstance(child, TextBlock):
                    imports.extend(_list_imports_for_block(child.text))
                elif isinstance(child, Section):
                    # Process nested sections
                    section_imports = _process_section_for_imports(child)
                    imports.extend(section_imports)
    
    # Remove duplicates while preserving order
    unique_imports = []
    for imp in imports:
        if imp not in unique_imports:
            unique_imports.append(imp)
    
    return unique_imports

def _list_imports_for_block(text: str) -> List[str]:
    """
    Extract imports from a text block using Claude.
    
    Args:
        text: The text content to analyze
        
    Returns:
        A list of import paths
    """
    # Use regex to find all [[path/to/file]] patterns
    import_pattern = r'\[\[(.*?)\]\]'
    matches = re.findall(import_pattern, text)
    
    # If no matches found using regex, try using Claude
    if not matches:
        # Create a chat instance with Claude Haiku
        system_prompt = """
        You are a dependency analyzer. Your task is to identify dependencies in markdown text.
        Dependencies are specified using the syntax [[path/to/file]].
        You must list these dependencies one per line, without any other text.
        If there are no dependencies, respond with "no dependencies".
        """
        
        chat = SimpleChat(system_prompt, model="claude-haiku")
        
        # Ask Claude to identify dependencies
        response = chat.call(
            "Identify all dependencies in this text that use the [[path/to/file]] syntax. List them one per line:\n\n{{ text }}",
            text=text
        )
        
        # Process the response
        if "no dependencies" in response.lower():
            return []
        
        # Split the response by lines and clean up
        potential_imports = [line.strip() for line in response.split('\n') if line.strip()]
        
        # Filter to only include valid import patterns
        matches = []
        for imp in potential_imports:
            # Extract the path from [[path]] if present
            import_match = re.search(r'\[\[(.*?)\]\]', imp)
            if import_match:
                matches.append(import_match.group(1))
            # If it's just a plain path without brackets, include it if it looks valid
            elif '/' in imp or '.' in imp:
                matches.append(imp)
    
    # Ensure all imports end with .md if they don't have an extension
    normalized_imports = []
    for imp in matches:
        if not os.path.splitext(imp)[1]:
            normalized_imports.append(f"{imp}.md")
        else:
            normalized_imports.append(imp)
    
    return normalized_imports

def _process_section_for_imports(section: Section) -> List[str]:
    """
    Process a section and its children for imports.
    
    Args:
        section: The section to process
        
    Returns:
        A list of import paths
    """
    imports = []
    
    for child in section.children:
        if isinstance(child, TextBlock):
            imports.extend(_list_imports_for_block(child.text))
        elif isinstance(child, Section):
            # Recursively process nested sections
            section_imports = _process_section_for_imports(child)
            imports.extend(section_imports)
    
    return imports

def describe_interface(spec_path: str) -> Section:
    """
    Find blocks that describe the interface of the module.
    
    Args:
        spec_path: Path to the specification document
        
    Returns:
        A Section block containing the interface description
    """
    blocks = parse_markdown(spec_path)
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Invalid specification document: {spec_path}")
    
    root_section = blocks[0]
    
    # Create a new section with the same title
    interface_section = Section(title=root_section.title, children=[])
    
    # Add top-level text blocks
    for child in root_section.children:
        if isinstance(child, TextBlock):
            interface_section.children.append(child)
    
    # Find interface-related sections
    for child in root_section.children:
        if isinstance(child, Section):
            if _is_interface_section(child):
                interface_section.children.append(child)
    
    # Process dependencies
    processed_deps = set()
    deps_to_process = list_imports(spec_path)
    
    # Process dependencies until we have no more to process
    while deps_to_process:
        dep = deps_to_process.pop(0)
        
        if dep in processed_deps:
            continue
        
        processed_deps.add(dep)
        
        # Resolve the dependency path
        dep_path = _resolve_import_path(dep, os.path.dirname(spec_path))
        
        try:
            # Get the interface of the dependency
            dep_interface = describe_interface(dep_path)
            
            # Add the dependency interface to our interface section
            interface_section.children.insert(0, dep_interface)
            
            # Add the dependency's dependencies to our list
            new_deps = list_imports(dep_path)
            for new_dep in new_deps:
                if new_dep not in processed_deps:
                    deps_to_process.append(new_dep)
        except FileNotFoundError as e:
            print(f"Error: Could not find dependency {dep}: {e}")
            raise
        except Exception as e:
            print(f"Error loading dependency {dep}: {e}")
            raise
    
    return interface_section

def _is_interface_section(section: Section) -> bool:
    """
    Determine if a section is likely describing the interface.
    
    Args:
        section: The section to check
        
    Returns:
        True if the section is likely an interface section, False otherwise
    """
    # Check if the section title suggests it's an interface section
    interface_keywords = ["interface", "usage", "api", "public", "exported"]
    
    # Convert to lowercase for case-insensitive matching
    title_lower = section.title.lower()
    
    # Check if any of the keywords are in the title
    for keyword in interface_keywords:
        if keyword in title_lower:
            return True
    
    # If not obvious from the title, use Claude to determine
    system_prompt = """
    You are an expert at identifying interface descriptions in software documentation.
    Your task is to determine if a section describes the interface or usage instructions for a module.
    Answer with only 'yes' or 'no'.
    """
    
    chat = SimpleChat(system_prompt, model="claude-haiku")
    
    # Convert the section to markdown for Claude to analyze
    from tlc.markdown_parser import render_markdown
    section_markdown = render_markdown([section])
    
    response = chat.call(
        "Does this section describe the interface or usage instructions for a module?\n\n{{ section }}",
        section=section_markdown
    )
    
    return response.lower().strip() == "yes"

def _resolve_import_path(import_path: str, base_dir: str) -> str:
    """
    Resolve an import path relative to the base directory.
    
    Args:
        import_path: The import path to resolve
        base_dir: The base directory to resolve from
        
    Returns:
        The resolved absolute path
    """
    # First try direct resolution
    direct_path = os.path.join(base_dir, import_path)
    if os.path.exists(direct_path):
        return direct_path
    
    # If that fails, try to find the file in subdirectories
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == os.path.basename(import_path):
                return os.path.join(root, file)
    
    # If still not found, raise an error
    raise FileNotFoundError(f"Could not find import {import_path} relative to {base_dir}")

def preprocess_spec_context(path: str) -> str:
    """
    Preprocess a specification document to include all required interfaces.
    
    Args:
        path: Path to the specification document
        
    Returns:
        A modified markdown document with interfaces prepended
    """
    try:
        # Get the interface description
        interface_section = describe_interface(path)
        
        # Convert the interface to markdown
        from tlc.markdown_parser import render_markdown
        interface_markdown = render_markdown([interface_section])
        
        # Read the original spec
        with open(path, "r") as f:
            original_spec = f.read()
        
        # Combine the interface and original spec
        return interface_markdown + "\n\n" + original_spec
    except FileNotFoundError as e:
        print(f"Error: Could not find file: {e}")
        raise
    except Exception as e:
        print(f"Error preprocessing spec: {e}")
        raise

def get_code_target(path: str) -> Optional[str]:
    """
    Get the name of the Python module this specification describes.
    
    Args:
        path: Path to the specification document
        
    Returns:
        The module name, or None if it's documentation only
    """
    blocks = parse_markdown(path)
    if not blocks or not isinstance(blocks[0], Section):
        raise ValueError(f"Invalid specification document: {path}")
    
    # Get the title of the root section
    title = blocks[0].title
    
    # Check if it ends with .py
    if title.endswith(".py"):
        return title
    # Check if it ends with .md (documentation only)
    elif title.endswith(".md"):
        return None
    else:
        raise ValueError(f"Invalid specification title: {title}. Must end with .py or .md")

def main():
    """CLI entry point for the specification document processor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process specification documents")
    parser.add_argument("command", choices=["preprocess"], help="Command to run")
    parser.add_argument("spec_path", help="Path to the specification document")
    
    args = parser.parse_args()
    
    if args.command == "preprocess":
        try:
            result = preprocess_spec_context(args.spec_path)
            print(result)
        except Exception as e:
            print(f"Error: {e}")
            exit(1)

if __name__ == "__main__":
    main() 