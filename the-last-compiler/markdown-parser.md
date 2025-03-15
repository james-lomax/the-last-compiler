# markdown_parser.py

Parse a markdown file into a tree of blocks for easier handling.

## Interface

Defines function parse_markdown(path: str) -> List[Block]

Parse a specification document as a markdown file. This allows us to ignore references defined with @path/to/file.md when we're reading code blocks, and allows us to keep some sections and discard others in the prompting.

Markdown files are parsed into a tree of Block objects.

Block is an abstract class.

Implementations:

- class TextBlock(Block)
    - text: str
- class CodeBlock(Block)
    - language: str
    - code: str
- class Section(Block)
    - title: str
    - children: list[Block]

## Implementation

Uses the mistune python library to parse the markdown AST and simplify it to the above form, rendering out paragraphs into TextBlocks.

```python
import mistune

def parse_markdown(path: str) -> List[Block]:
    with open(path, "r") as f:
        markdown = f.read()
        # todo hmm
    return mistune.parse(markdown)
```

todo hmm
