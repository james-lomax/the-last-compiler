# markdown_parser.py

Parse a markdown file into a tree of blocks for easier handling.

## Python dependencies

- mistune

## Interface

Defines function parse_markdown(path: str) -> List[Block]

Parse a specification document as a markdown file. This allows us to ignore references defined with `[[path/to/file]]` when we're reading code blocks, and allows us to keep some sections and discard others in the prompting.

Markdown files are parsed into a tree of Block objects.

Block is an abstract class.

Implementations (dataclass definitions):

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

### Using mistune

Mistune creates an AST from Markdown

```python
import mistune

parser = mistune.create_markdown(renderer=None)
ast = parser(markdown)
```

For example, for the following markdown document:

```markdown
# Top level heading

Introduction

## Second level heading

Paragraph

```python
import os
```

List:
- Item 1
- Item 2
    - Item 2.1
    - Item 2.2
- Item 3
```

The AST is:

```json
[
  {
    "type": "heading",
    "attrs": {
      "level": 1
    },
    "style": "atx",
    "children": [
      {
        "type": "text",
        "raw": "Top level heading"
      }
    ]
  },
  {
    "type": "blank_line"
  },
  {
    "type": "paragraph",
    "children": [
      {
        "type": "text",
        "raw": "Introduction"
      }
    ]
  },
  {
    "type": "blank_line"
  },
  {
    "type": "heading",
    "attrs": {
      "level": 2
    },
    "style": "atx",
    "children": [
      {
        "type": "text",
        "raw": "Second level heading"
      }
    ]
  },
  {
    "type": "blank_line"
  },
  {
    "type": "paragraph",
    "children": [
      {
        "type": "text",
        "raw": "Paragraph"
      }
    ]
  },
  {
    "type": "blank_line"
  },
  {
    "type": "block_code",
    "raw": "import os\n",
    "style": "fenced",
    "marker": "```",
    "attrs": {
      "info": "python"
    }
  },
  {
    "type": "blank_line"
  },
  {
    "type": "paragraph",
    "children": [
      {
        "type": "text",
        "raw": "List:"
      }
    ]
  },
  {
    "type": "list",
    "children": [
      {
        "type": "list_item",
        "children": [
          {
            "type": "block_text",
            "children": [
              {
                "type": "text",
                "raw": "Item 1"
              }
            ]
          }
        ]
      },
      {
        "type": "list_item",
        "children": [
          {
            "type": "block_text",
            "children": [
              {
                "type": "text",
                "raw": "Item 2"
              }
            ]
          },
          {
            "type": "list",
            "children": [
              {
                "type": "list_item",
                "children": [
                  {
                    "type": "block_text",
                    "children": [
                      {
                        "type": "text",
                        "raw": "Item 2.1"
                      }
                    ]
                  }
                ]
              },
              {
                "type": "list_item",
                "children": [
                  {
                    "type": "block_text",
                    "children": [
                      {
                        "type": "text",
                        "raw": "Item 2.2"
                      }
                    ]
                  }
                ]
              }
            ],
            "tight": true,
            "bullet": "-",
            "attrs": {
              "depth": 1,
              "ordered": false
            }
          }
        ]
      },
      {
        "type": "list_item",
        "children": [
          {
            "type": "block_text",
            "children": [
              {
                "type": "text",
                "raw": "Item 3"
              }
            ]
          }
        ]
      }
    ],
    "tight": true,
    "bullet": "-",
    "attrs": {
      "depth": 0,
      "ordered": false
    }
  }
]
```

#### Creating a tree structure from the AST

We need to collect all the sections of the document into a tree structure, with all blocks as children of the titled section, and with sections being children of their parent section.

We can turn this into the tree structure we want by iterating through the top level AST items - each top level item in the AST can be represented as a single Block, which internally contains the AST node for the block (allowing us to render it back to markdown if needed), but also allows us to read the important fields of the block. The Section class will not keep its own AST node, but will recreate it with the correct section level.

let section_stack be a stack of Section objects (initially empty)

At any time, let current_level be the size of the section_stack.

At any time, let current_section be the section at the top of the section_stack.

The first item in the AST is always a level 1 heading, which we use to instantiate current_section. Fail if this is not the case.

For each top level item in the AST:

- If the item is a heading:
    - If the heading level is 1 greater than the current_level:
        - Create a new Section with this heading
        - Add this new Section to the children of current_section
        - Push this new Section onto the section_stack
    - If the heading level is less than the current_level:
        - Pop from section_stack until the heading level is one above current_section.level
        - Add the current item to the children of the section at the top of the stack
        - Push this new Section onto the section_stack
    - If the heading level is equal to the current_level:
        - Add the current item to the children of the current_section
    - Otherwise, if the heading level is more than 1 greater than the current_level:
        - Fail with an error
- If the item is a paragraph:
    - Create a TextBlock with the paragraph text - render markdown completely from this AST node (we don't care about the structure within the paragraph)
    - Add this TextBlock to the children of the current_section
- If the item is a list:
    - Create a TextBlock with the list text - render markdown completely from this AST node (we don't care about the structure within the paragraph)
    - Add this ListBlock to the children of the current_section
- If the item is a block_code:
    - Create a CodeBlock with the code and language
    - Add this CodeBlock to the children of the current_section
- If the item is a blank_line:
    - Ignore

#### Rendering back to markdown

To render an AST (a list of nodes) we can use the MarkdownRenderer.

```python
from mistune.renderers.markdown import MarkdownRenderer

ast = [...]

renderer = MarkdownRenderer()
result = renderer(ast, mistune.BlockState())
```

To render Section objects, we need to implement a make_ast method on all Block classes which gets the list of AST nodes that describes the block ready for rendering. The Section block will not maintain its own AST, but will create the list of AST nodes for its children, prepend a heading node at the correct level, and return the whole list. A section_level argument will be passed in to make_ast to indicate the level of the section, incremented as we recurse into nested sections.

### CLI

For testing purposes, implement a CLI that takes a markdown file and prints our internal tree structure. We will use dataclasses-json to serialize the tree structure to JSON. The CLI will take an input file, and print the JSON to stdout.
