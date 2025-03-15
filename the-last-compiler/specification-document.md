# specification_document.py

This module provides utilities for pre-processing specification documents to be used by the compiler.

## Dependencies

- [[llm/simple-chat-chain]]
- [[markdown-parser]]
- [[module-spec-files]]

## Usage

Depends on the block structure defined in [[markdown-parser]]

```python
imports = list_imports("specification-document.md") # ["llm/simple-chat-chain.md", "markdown-parser.md"]

describe_interface("specification-document.md") # Returns a SectionBlock with the same title as the spec, but only the sub-blocks that describe the interface of the module, and the interfaces of the modules required to understand this interface

preprocess_spec_context("specification-document.md") # Returns a modified markdown document with the described interfaces prepended to the spec

get_code_target("specification-document.md") # Returns the name of the python module this specification describes, or None if it does not describe a module (i.e. is just documentation)
```

## Implementation

Parse the markdown file into a Section using [[markdown-parser]]

### def list_imports(spec_path: str) -> List[str]

List imports for the whole file by passing each text block into list_import_for_block which:

- Ask claude-haiku to list the imports
    - the system prompt will tell Claude it must consider `[[path/to/file]]` as a dependency and save list the dependencies line by line
    - In the system prompt, instruct the model to return only the dependencies, one per line, without any other text. Instruct the model to return "no dependencies" if it can't find any dependencies, and find this text in the response to skip the rest of the function and return an empty list.

### def describe_interface(spec_path: str) -> SectionBlock

Finds all the blocks that are likely to describe the interface of the module. Will have titles like "Interface" or "Usage".

For each second level block (`##`), ask claude-haiku if the block with this title is likely describing the interface or usage instructions for the module by other python modules. Include any second level block which is describing the interface of the module in the output context block. Also include any top level TextBlock in the output context block.

Once we've created the SectionBlock with only the relevant blocks, we call list_imports() on it to get the dependencies that are required to understand this interface, then we load those files (remember that these files are relative to the spec file, not the current working directory), call describe_interface() on them, and prepend the result to the SectionBlock (this is the extra required context that is needed to understand the interface). We ignore dependencies already in this interface, and we stop when we have no more dependencies to load.

#### Import Resolution and Error Handling

- All imports are resolved relative to the spec file's directory, not the current working directory
- If the import is specified without a complete path, we should also search sub-directories from the current spec's parent folder to attempt to find a matching module name.
- If a dependency file cannot be found, the function must print an error message and fail by raising a FileNotFoundError
- If there's an error loading a dependency, the function must print an error message and fail by re-raising the exception
- The function should not continue processing or add error messages to the returned SectionBlock when a dependency cannot be found or loaded

### def preprocess_spec_context(path: str) -> str

A convenience function that:
1. Loads a specification document using load_specification_document
2. Calls describe_interface with the correct spec_path to ensure proper relative import resolution
3. Handles and re-raises any exceptions with appropriate error messages
4. Returns a modified markdown document with the described interfaces prepended to the spec

### get_code_target(path: str): str

Returns the name of the python module this specification describes, or None if it does not describe a module (i.e. is just documentation).

All spec documents start with a level 1 heading with the name of the target module. If the level 1 heading ends in `.py` then this is the module name, return it. If it ends in `.md` then return None, this is documentation only. Otherwise, fail with a suitable error.

### CLI

This module implements a CLI with one command `preprocess <spec-path>` which will preprocess the spec document into the context-free spec.
