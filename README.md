# The Last Compiler (TLC)

The future is here. Claude Sonnet 3.7 is more-or-less capable of turning any sufficiently well defined specification into a working python module in one go.

English is the last programming language humans will ever need.

## What is TLC?

TLC takes markdown documents containing specifications for Python modules and uses Claude Code to generate the corresponding Python code. It evaluates whether the specification is well-defined enough to implement, and if so, creates the module and updates your project configuration.

## Installation

### Prerequisites

- [uv](https://github.com/astral-sh/uv) - The Python package installer and resolver
- [claude-code](https://github.com/anthropics/claude-code) - This tool simply launches claude-code to turn your spec into code

### Install TLC

```bash
# Clone the repository
git clone https://github.com/jameslomax/TheLastCompiler.git
cd TheLastCompiler

# Install the tool with uv
uv tool install .
```

## Usage

Once installed, you can start a new project with:

```bash
uv init my_project
cd my_project
```

Write your module specification files describing what the code should do. Then use the `tlc` command to compile the markdown specifications into a python module:

```bash
tlc module_specification.md
```

The tool will:
1. Evaluate if the specification is well-defined
2. Generate the Python module at `tlc/module_name.py`
3. Update the pyproject.toml file
4. Implement tests if specified

### Specification recommendations

- Be clear about the inputs and outputs of the module
- Specify if how to test the module

## Bootstrapping

the_last_compiler.md can be used to bootstrap the code in this project - compiling itself into a working python module which can compile Markdown specifications into Python modules.

```bash
./bootstrap.sh
```
