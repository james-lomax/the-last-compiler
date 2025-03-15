# specification_document.py

This module provides utilities for pre-processing specification documents to be used by the compiler.

## Dependencies

- [[llm/simple-chat-chain]]
- [[markdown-parser]]
- [[module-spec-files]]

## Usage

Depends on the block structure defined in [[markdown-parser]]

```python
preprocess_spec_context("specification-document.md") # Returns a modified markdown document with the described interfaces prepended to the spec

get_code_target("specification-document.md") # Returns the name of the python module this specification describes, or None if it does not describe a module (i.e. is just documentation)
```

## Implementation

Parse the markdown file into a Section using [[markdown-parser]]

### def list_import_for_block(block: TextBlock) -> List[str]

- Checks if there are any strings in the block match `\[\[([a-zA-Z\d \-\/]+)\]\]` and extracts the dependency name

This parses out dependencies from the text block which are described in Obsidian form, i.e.:

```
Reference to [[file]] or [[path/to/file]]
```

The returned list of import file names must have an extension. If there is no extension, add `.md` to the end of the filename.
### def describe_dependency_interfaces(spec_path: str) -> Section

Describes all the interfaces that we need to be aware of to implement this module - visits all dependencies of the spec file and collects the exported API details from each spec file we depend on.

- We create a list of `dependencies_to_visit` that are required to understand this interface by calling `list_import_for_block` on all `TextBlock`s in the spec file
- Then we loop while we still have `dependencies_to_visit`
	- We call `get_public_interface_blocks` on each unvisited dependency
	- We call list_import_for_block on all the TextBlocks in the dependency we are visiting
	- We add any new unvisited dependencies to the to_visit list
- When this loop is finished we have a complete set of interface descriptions that is required for this file

#### def get_public_interface_blocks(spec_path: str) -> Section

This function reads the spec file, and for each second level block (`##`), checks if the title is "Interface", "Usage", "Api",  "public" or "exported" (ignore case) and therefore this block is describing the interface or usage instructions for the module by other python modules. Include any second level block which is describing the interface of the module in the output Section. Also include any top level TextBlock in the output.

#### Import Resolution and Error Handling

- All imports are resolved relative to the spec file's directory, not the current working directory
- If the import is specified without a complete path, we should also search sub-directories from the current spec's parent folder to attempt to find a matching module name.
- If a dependency file cannot be found, the function must print an error message and fail by raising a FileNotFoundError
- If there's an error loading a dependency, the function must print an error message and fail by re-raising the exception
- The function should not continue processing or add error messages to the returned SectionBlock when a dependency cannot be found or loaded

### def preprocess_spec_context(path: str) -> str

A convenience function that:
1. Loads a specification document using load_specification_document
2. Calls describe_dependency_interfaces with the correct spec_path to ensure proper relative import resolution
3. Handles and re-raises any exceptions with appropriate error messages
4. Returns a modified markdown document with the described interfaces prepended to the spec

### get_code_target(path: str): str

Returns the name of the python module this specification describes, or None if it does not describe a module (i.e. is just documentation).

All spec documents start with a level 1 heading with the name of the target module. If the level 1 heading ends in `.py` then this is the module name, return it. If it ends in `.md` then return None, this is documentation only. Otherwise, fail with a suitable error.

### CLI

This module implements a CLI with one command `preprocess <spec-path>` which will preprocess the spec document into the context-free spec.
