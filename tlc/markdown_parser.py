import mistune
from mistune.renderers.markdown import MarkdownRenderer
from dataclasses import dataclass
from typing import List, Optional, Any
from dataclasses_json import dataclass_json

# Abstract base class for all blocks
@dataclass_json
@dataclass
class Block:
    """Abstract base class for all blocks in the markdown tree."""
    def make_ast(self, section_level: int = 0) -> List[Any]:
        """Convert the block to an AST representation for rendering."""
        raise NotImplementedError("Subclasses must implement make_ast")

@dataclass_json
@dataclass
class TextBlock(Block):
    """A block of text content."""
    text: str
    
    def make_ast(self, section_level: int = 0) -> List[Any]:
        """Convert the text block to an AST representation."""
        return [{
            "type": "paragraph",
            "children": [
                {
                    "type": "text",
                    "raw": self.text
                }
            ]
        }]

@dataclass_json
@dataclass
class CodeBlock(Block):
    """A block of code with a specified language."""
    language: str
    code: str
    
    def make_ast(self, section_level: int = 0) -> List[Any]:
        """Convert the code block to an AST representation."""
        return [{
            "type": "block_code",
            "raw": self.code,
            "style": "fenced",
            "marker": "```",
            "attrs": {
                "info": self.language
            }
        }]

@dataclass_json
@dataclass
class Section(Block):
    """A section with a title and child blocks."""
    title: str
    children: List[Block]
    
    def make_ast(self, section_level: int = 0) -> List[Any]:
        """Convert the section to an AST representation, including all children."""
        # Create the heading node
        ast = [{
            "type": "heading",
            "attrs": {
                "level": section_level + 1
            },
            "style": "atx",
            "children": [
                {
                    "type": "text",
                    "raw": self.title
                }
            ]
        }, {
            "type": "blank_line"
        }]
        
        # Add all children's AST nodes
        for child in self.children:
            child_ast = child.make_ast(section_level + 1)
            ast.extend(child_ast)
            # Add a blank line after each child
            if child_ast:
                ast.append({"type": "blank_line"})
        
        return ast
    

class InlineMarkdownRenderer(MarkdownRenderer):
    def strikethrough(self, token, state):
        return '~~' + self.render_children(token, state) + '~~'
    
    def link(self, token, state):
        return f"[{self.render_children(token, state)}]({token['href']})"
    
    def emphasis(self, token, state):
        return '*' + self.render_children(token, state) + '*'
    
    def strong(self, token, state):
        return '**' + self.render_children(token, state) + '**'
    
    def codespan(self, token, state):
        return f'`{token["raw"]}`'

def _extract_text(node: dict) -> str:
    """Extract text from a node that may contain children with text."""
    renderer = InlineMarkdownRenderer()
    return renderer([node], mistune.BlockState())

def _render_ast_to_text(ast: List[dict]) -> str:
    """Render an AST to plain text."""
    renderer = InlineMarkdownRenderer()
    return renderer(ast, mistune.BlockState())

def _process_ast(ast: List[dict]) -> List[Block]:
    """Process the AST into our Block structure."""
    if not ast or ast[0].get("type") != "heading" or ast[0].get("attrs", {}).get("level") != 1:
        raise ValueError("Markdown document must start with a level 1 heading")
    
    # Initialize with the root section
    root_title = _extract_text(ast[0])
    root_section = Section(title=root_title, children=[])
    section_stack = [root_section]
    current_level = 1
    
    # Skip the first heading as we've already processed it
    for item in ast[1:]:
        item_type = item.get("type")
        
        # Skip blank lines
        if item_type == "blank_line":
            continue
        
        # Process headings to build the section hierarchy
        if item_type == "heading":
            heading_level = item.get("attrs", {}).get("level", 1)
            heading_text = _extract_text(item)
            
            if heading_level == current_level:
                # Same level as current section, create a sibling section
                parent_section = section_stack[-2] if len(section_stack) > 1 else None
                if parent_section:
                    new_section = Section(title=heading_text, children=[])
                    parent_section.children.append(new_section)
                    section_stack.pop()
                    section_stack.append(new_section)
            elif heading_level == current_level + 1:
                # One level deeper, create a child section
                new_section = Section(title=heading_text, children=[])
                section_stack[-1].children.append(new_section)
                section_stack.append(new_section)
                current_level += 1
            elif heading_level < current_level:
                # Going back up the hierarchy
                while current_level > heading_level:
                    section_stack.pop()
                    current_level -= 1
                
                # Create a new section at this level
                parent_section = section_stack[-2] if len(section_stack) > 1 else None
                if parent_section:
                    new_section = Section(title=heading_text, children=[])
                    parent_section.children.append(new_section)
                    section_stack.pop()
                    section_stack.append(new_section)
            else:
                # Heading level skips one or more levels, which is an error
                raise ValueError(f"Heading level {heading_level} skips one or more levels from current level {current_level}")
        
        # Process paragraphs
        elif item_type == "paragraph":
            text = _extract_text(item)
            section_stack[-1].children.append(TextBlock(text=text))
        
        # Process code blocks
        elif item_type == "block_code":
            language = item.get("attrs", {}).get("info", "")
            code = item.get("raw", "")
            section_stack[-1].children.append(CodeBlock(language=language, code=code))
        
        # Process lists by converting them to text
        elif item_type == "list":
            # For lists, we'll render them back to markdown and store as text
            list_text = _render_ast_to_text([item])
            section_stack[-1].children.append(TextBlock(text=list_text))
    
    return [root_section]

def parse_markdown(path: str) -> List[Block]:
    """
    Parse a markdown file into a tree of blocks.
    
    Args:
        path: Path to the markdown file
        
    Returns:
        A list containing the root Block (usually a Section)
    """
    with open(path, "r") as f:
        markdown = f.read()
    
    # Parse the markdown to AST
    parser = mistune.create_markdown(renderer=None)
    ast = parser(markdown)
    
    # Process the AST into our Block structure
    return _process_ast(ast)

def render_markdown(blocks: List[Block]) -> str:
    """
    Render a list of blocks back to markdown.
    
    Args:
        blocks: List of Block objects
        
    Returns:
        Markdown string
    """
    ast = []
    for block in blocks:
        ast.extend(block.make_ast())
    
    renderer = InlineMarkdownRenderer()
    return renderer(ast, mistune.BlockState())

# CLI for testing
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python markdown_parser.py <markdown_file>")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    blocks = parse_markdown(markdown_file)
    
    # Convert to JSON and print
    json_output = json.dumps([block.to_dict() for block in blocks], indent=2)
    print(json_output) 

    # Render back to markdown
    markdown = render_markdown(blocks)
    print(markdown)
