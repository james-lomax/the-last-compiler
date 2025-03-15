import os
import sys
import json
from pathlib import Path
from markdown_parser import parse_markdown, render_markdown, Section, TextBlock, CodeBlock

def test_parse_and_render():
    """Test parsing a markdown file and rendering it back."""
    # Get the path to the markdown-parser.md file
    current_dir = Path(__file__).parent.parent
    test_file = current_dir / "markdown-parser.md"
    
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return False
    
    # Parse the markdown file
    blocks = parse_markdown(str(test_file))
    
    # Verify we got a list with at least one Section
    if not blocks or not isinstance(blocks[0], Section):
        print("Failed to parse markdown into a Section")
        return False
    
    # Print the structure
    print("Parsed structure:")
    print_structure(blocks[0])
    
    # Render back to markdown
    markdown = render_markdown(blocks)
    
    # Print the first 500 characters of the rendered markdown
    print("\nRendered markdown (first 500 chars):")
    print(markdown[:500])
    
    return True

def print_structure(block, indent=0):
    """Print the structure of a block tree."""
    if isinstance(block, Section):
        print(f"{' ' * indent}Section: {block.title}")
        for child in block.children:
            print_structure(child, indent + 2)
    elif isinstance(block, TextBlock):
        print(f"{' ' * indent}TextBlock: {block.text[:50]}...")
    elif isinstance(block, CodeBlock):
        print(f"{' ' * indent}CodeBlock ({block.language}): {block.code[:50]}...")
    else:
        print(f"{' ' * indent}Unknown block type: {type(block)}")

if __name__ == "__main__":
    success = test_parse_and_render()
    sys.exit(0 if success else 1) 