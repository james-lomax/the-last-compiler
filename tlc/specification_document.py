import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from .llm.langchain_logging import save_logs
from .markdown_parser import Section, TextBlock, CodeBlock, parse_markdown

class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected in spec files."""
    pass

class ParseError(Exception):
    """Raised when markdown parsing fails."""
    pass

def list_import_for_block(block: TextBlock) -> List[str]:
    """Extract dependency names from a text block in Obsidian format.

    Args:
        block: The text block to analyze.

    Returns:
        List of dependency file names with extensions.
    """
    pattern = r'\[\[([a-zA-Z\d \-\/]+)\]\]'
    matches = re.findall(pattern, block.content)
    
    # Add .md extension if missing
    return [f"{m}.md" if '.' not in m else m for m in matches]

def get_public_interface_blocks(spec_path: str) -> Section:
    """Extract public interface blocks from a spec file.

    Args:
        spec_path: Path to the specification file.

    Returns:
        Section containing interface blocks and top-level text.

    Raises:
        FileNotFoundError: If spec file doesn't exist.
        ParseError: If markdown is malformed.
    """
    try:
        doc = parse_markdown(spec_path)
    except Exception as e:
        raise ParseError(f"Failed to parse {spec_path}: {str(e)}")

    interface_section = Section("Interfaces")
    interface_keywords = {"interface", "usage", "api", "public", "exported"}

    # Add top-level text blocks
    for block in doc.blocks:
        if isinstance(block, TextBlock):
            interface_section.add_block(block)

    # Add interface blocks
    for block in doc.blocks:
        if isinstance(block, Section) and block.level == 2:
            if block.title.lower().strip() in interface_keywords:
                interface_section.add_block(block)

    return interface_section

def find_spec_file(base_dir: Path, spec_name: str, visited: Set[Path] = None, depth: int = 0) -> Optional[Path]:
    """Find a spec file in the directory tree.

    Args:
        base_dir: Starting directory for search.
        spec_name: Name of spec file to find.
        visited: Set of visited directories to prevent cycles.
        depth: Current recursion depth.

    Returns:
        Path to spec file if found, None otherwise.
    """
    if visited is None:
        visited = set()
    if depth > 5 or base_dir in visited:
        return None
    
    visited.add(base_dir)
    matches = list(base_dir.rglob(spec_name))
    
    if len(matches) > 1:
        print(f"Warning: Multiple matches found for {spec_name}, using first match")
    
    return matches[0] if matches else None

def describe_dependency_interfaces(spec_path: str, visited: Set[str] = None) -> Section:
    """Collect all required interface descriptions for a spec file.

    Args:
        spec_path: Path to the specification file.
        visited: Set of visited spec files to prevent cycles.

    Returns:
        Section containing all required interfaces.

    Raises:
        CircularDependencyError: If circular dependency is detected.
        FileNotFoundError: If dependency cannot be found.
    """
    if visited is None:
        visited = set()
    
    if spec_path in visited:
        raise CircularDependencyError(f"Circular dependency detected: {' -> '.join(visited)} -> {spec_path}")
    
    visited.add(spec_path)
    dependencies_to_visit = set()
    collected_interfaces = Section("Dependencies", [])
    spec_dir = Path(spec_path).parent

    # Get initial dependencies
    doc = parse_markdown(spec_path)
    for block in doc:
        if isinstance(block, (TextBlock, CodeBlock)):
            dependencies_to_visit.update(list_import_for_block(block))

    # Process dependencies
    while dependencies_to_visit:
        dep = dependencies_to_visit.pop()
        dep_path = find_spec_file(spec_dir, dep)
        
        if not dep_path:
            raise FileNotFoundError(f"Dependency {dep} not found relative to {spec_path}")

        interface_blocks = get_public_interface_blocks(str(dep_path))
        
        # Add new dependencies from interface blocks
        for block in interface_blocks.blocks:
            if isinstance(block, (TextBlock, CodeBlock)):
                new_deps = set(list_import_for_block(block))
                dependencies_to_visit.update(new_deps - visited)
        
        collected_interfaces.children.append(interface_blocks)

    visited.remove(spec_path)
    return collected_interfaces

def setup_tlc_directory(spec_path: str) -> Path:
    """Create and setup the tlc directory structure.

    Args:
        spec_path: Path to the specification file.

    Returns:
        Path to the created tlc directory.
    """
    spec_dir = Path(spec_path).parent
    tlc_dir = spec_dir / "tlc"
    logs_dir = tlc_dir / "logs"

    # Create directories
    tlc_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Create __init__.py if it doesn't exist
    init_file = tlc_dir / "__init__.py"
    if not init_file.exists():
        init_content = """# This file was generated by tlc, the package here is managed by AI and therefore
# might not be worth reading, it is generated by the specifications in the parent directory"""
        init_file.write_text(init_content, encoding='utf-8')
        init_file.chmod(0o644)

    return tlc_dir

def get_code_target(spec_path: str) -> Optional[str]:
    """Get the target Python module name from a spec file.

    Args:
        spec_path: Path to the specification file.

    Returns:
        Module name if spec describes a Python module, None if documentation only.

    Raises:
        ValueError: If spec has invalid title format.
    """
    doc = parse_markdown(spec_path)
    if not doc or not isinstance(doc[0], Section):
        raise ValueError(f"Spec {spec_path} must start with a level 1 heading")

    title = doc[0].title.strip()
    if title.endswith('.py'):
        return title
    elif title.endswith('.md'):
        return None
    else:
        raise ValueError(f"Invalid spec title format in {spec_path}: {title}")

def preprocess_spec_context(spec_path: str) -> str:
    """Preprocess a spec file by collecting and prepending dependency interfaces.

    Args:
        spec_path: Path to the specification file.

    Returns:
        Modified markdown content with prepended interfaces.

    Raises:
        Various exceptions for file, parsing, and dependency errors.
    """
    try:
        # Setup directory structure
        tlc_dir = setup_tlc_directory(spec_path)
        
        # Get interfaces
        interfaces = describe_dependency_interfaces(spec_path)
        
        # Load original spec
        with open(spec_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Combine content
        processed_content = f"# Dependencies\n\n{interfaces}\n\n{original_content}"
        
        # Save preprocessed spec
        spec_name = Path(spec_path).stem
        output_path = tlc_dir / f"{spec_name}.no-context.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        return processed_content
    
    except Exception as e:
        raise type(e)(f"Error preprocessing {spec_path}: {str(e)}")

def main():
    """CLI entry point for preprocessing spec documents."""
    if len(sys.argv) != 3 or sys.argv[1] != "preprocess":
        print("Usage: python -m specification_document preprocess <spec-path>")
        sys.exit(1)

    spec_path = sys.argv[2]
    try:
        # Setup logging
        log_dir = Path(spec_path).parent / "tlc" / "logs"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        spec_name = Path(spec_path).stem
        
        processed_content = preprocess_spec_context(spec_path)
        print(f"Successfully preprocessed {spec_path}")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        save_logs()

if __name__ == "__main__":
    main()