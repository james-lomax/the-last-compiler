# init.py

## Usage
```
tlc init tool-name
```

Initialises a project with tlc, adding templated files.

### Output directory structure:

```
- tool-name/
	- USAGE.md
	- pyproject.toml
	- tool_name/
		- __main__.py
		- my-module.md
		- tlc/
			- __init__.py
```
## Implementation
Use Jinja2 for templates

Calls `uv init tool-name`

Overwrites `tool-name/pyproject.toml`:
```jinja2
[project]
name = "{{tool-name}}"
version = "0.1.0"
description = ""
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
{{tool-name}} = "{{tool-name}}.tlc:main"
```
Creates `tool-name/tool_name/`
Adds `tool-name/USAGE.md`
```markdown
# tool-name

TODO: Describe how this tool is used
```
Adds `tool-name/tool_name/tlc/__main__.py`:
```python
import sys
import importlib

def main() -> None:
    if len(sys.argv) < 2:
        print("Error: Command required", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    sys.argv.pop(1)  # Remove the command from argv

    try:
        module = importlib.import_module(f".{command}", package="__main__")
        module.main()
    except ImportError as e:
        print(f"Error: Could not import module '{command}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error executing command '{command}': {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```
Create an empty file at `tool-name/tool_name/tlc/__init__.py` and `tool_name/tool-name/tlc/__init__.py`

Adds `my-module.md` :
```markdown
# my_module.py

Reference other specifications with `[[other-module-name]]`

## Usage

TODO: Describe how to use this tool

## Interface

TODO: Describe the interface of this tool

## Implementation

TODO: Describe how this module is implemented.

Make sure your module adheres to the principals of SOLID.

```