# specification_document.py

This module provides utilities for pre-processing specification documents to be used by the compiler.

## Usage

Depends on the block structure defined in [[markdown-parser]]

```python
imports = list_imports("specification-document.md") # ["llm/simple-chat-chain.md", "markdown-parser.md"]

describe_interface("specification-document.md") # Returns a SectionBlock with the same title as the spec, but only the sub-blocks that describe the interface of the module, and the interfaces of the modules required to understand this interface

preprocess_spec_context("specification-document.md") # Returns a modified markdown document with the described interfaces prepended to the spec
```
