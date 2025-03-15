# specification_document.py

## Dependencies

- @llm/simple-chat-chain.md
- @markdown-parser.md

## Usage

Depends on the block structure defined in @markdown-parser.md

```python
# Load a markdown document
spec = parse_markdown("specification-document.md")

imports = list_imports(spec) # ["llm/simple-chat-chain.md", "markdown-parser.md"]

describe_interface(spec) # Returns a SectionBlock with the same title as the spec, but only the sub-blocks that describe the interface of the module, and the interfaces of the modules required to understand this interface

spec.text # all blocks formatted as a single string
```

## Implementation

### def load_specification_document(path: str) -> SectionBlock

Parse the markdown spec using @markdown-parser.md

### def list_imports(spec: SectionBlock) -> List[str]

List imports for the whole file by passing each text block into list_import_for_block which:

- Ask claude-haiku to list the imports
    - the system prompt will tell Claude it must consider `@path/to/file.md` as a dependency and save list the dependencies line by line

### def describe_interface(spec: SectionBlock) -> SectionBlock

Finds all the blocks that are likely to describe the interface of the module. Will have titles like "Interface" or "Usage".

For each second level block (`##`), ask claude-haiku if the block with this title is likely describing the interface or usage instructions for the module by other python modules.

Once we've created the SectionBlock with only the relevant blocks, we call list_imports() on it to get the dependencies that are required to understand this interface, then we load those files, call describe_interface() on them, and prepend the result to the SectionBlock (this is the extra required context that is needed to understand the interface). We ignore dependencies already in this interface, and we stop when we have no more dependencies to load.
