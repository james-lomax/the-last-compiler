#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import jinja2
from pathlib import Path

# Jinja2 templates for prompts
CLAUDE_PROMPT_TEMPLATE = """
# Instructions for implementing a Python module

Read the spec below and consider its feasibility: is it well defined enough to implement in a single python module? Are there any important unanswered questions? Are there any things you don't know how to do? Are any of these blockers to proceeding?

If no, Stop, and summarise why you cannot yet implement this spec as an error.

If yes, describe what we need to do to implement this module, then implement it.

The module should be created at tlc/{{ module_name }}.py
{% if test_strategy %}
If a test strategy is specified, implement it in tlc/tests/test_{{ module_name }}.py
{% endif %}

Update the pyproject.toml file to add the new module entry point, using this format:
```python
[project.scripts]
{{ command_name }} = "tlc.{{ module_name }}:main"
```

This script should be sufficient to implement the module. You must only add the {{ module_name }}.py module and edit the pyproject.toml file if needed.

# Module Specification
{{ specification }}
"""

NEW_MODULE_TEMPLATE = """# {module_name}.py

## Inputs

TODO define inputs

## Outputs

TODO define outputs

## Implementation

TODO define implementation. Be really specific about what code to write, and where to write it.
"""


def convert_name(name):
    """Convert between markdown file name and Python module name."""
    if name.endswith('.md'):
        # my-module-name.md -> my_module_name
        return name[:-3].replace('-', '_')
    else:
        # my_module_name -> my-module-name.md
        return name.replace('_', '-') + '.md'


def render_prompt(spec_path):
    """Render the Claude prompt using the specification markdown file."""
    with open(spec_path, 'r') as f:
        spec_content = f.read()
    
    module_name = convert_name(os.path.basename(spec_path))
    command_name = module_name.replace('_', '-')
    
    # Extract test strategy info - simple check if tests are mentioned
    test_strategy = "test" in spec_content.lower()
    
    template = jinja2.Template(CLAUDE_PROMPT_TEMPLATE)
    prompt = template.render(
        module_name=module_name,
        command_name=command_name,
        specification=spec_content,
        test_strategy=test_strategy
    )
    
    # Ensure the prompt directory exists
    os.makedirs('bin/prompt', exist_ok=True)
    
    # Write the prompt to the expected location
    with open('bin/prompt/the_last_compiler.md', 'w') as f:
        f.write(prompt)
    
    return prompt


def run_claude_code():
    """Run Claude Code with the generated prompt."""
    cmd = 'claude "Follow the instructions in bin/prompt/the_last_compiler.md"'
    return subprocess.call(cmd, shell=True)


def create_new_module(module_name):
    """Create a new markdown template file for a module."""
    if not module_name.endswith('.md'):
        module_name += '.md'
    
    # Check if file already exists
    if os.path.exists(module_name):
        print(f"Error: File {module_name} already exists")
        return False
    
    # Create the new markdown file
    with open(module_name, 'w') as f:
        python_module_name = os.path.basename(module_name).replace('-', '_')
        if python_module_name.endswith('.md'):
            python_module_name = python_module_name[:-3]
        
        content = NEW_MODULE_TEMPLATE.format(module_name=python_module_name)
        f.write(content)
    
    print(f"Created new module specification at {module_name}")
    return True


def compile_module(spec_path):
    """Compile the module specified in the markdown file."""
    if not os.path.exists(spec_path):
        print(f"Error: Specification file {spec_path} not found")
        return False
    
    render_prompt(spec_path)
    print(f"Compiling module from {spec_path}...")
    return run_claude_code()


def ensure_module_compiled(spec_path):
    """Ensure the module is compiled before running/testing it."""
    module_name = convert_name(os.path.basename(spec_path))
    module_path = f"tlc/{module_name}.py"
    
    if not os.path.exists(module_path):
        print(f"Module not found. Compiling {spec_path} first...")
        if not compile_module(spec_path):
            return False
    return True


def test_module(spec_path):
    """Test the module specified in the markdown file."""
    if not ensure_module_compiled(spec_path):
        return False
    
    module_name = convert_name(os.path.basename(spec_path))
    test_path = f"tlc/tests/test_{module_name}.py"
    
    if not os.path.exists(test_path):
        print(f"No tests found at {test_path}")
        return False
    
    print(f"Running tests for {module_name}...")
    return subprocess.call([sys.executable, "-m", "pytest", test_path])


def run_module(spec_path, args):
    """Run the module specified in the markdown file with arguments."""
    if not ensure_module_compiled(spec_path):
        return False
    
    module_name = convert_name(os.path.basename(spec_path))
    command_name = module_name.replace('_', '-')
    
    print(f"Running {command_name} with args: {' '.join(args)}")
    cmd = ["uv", "run", command_name] + args
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(description="The Last Compiler - compile markdown specs to Python modules")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to run")
    
    # tlc new
    new_parser = subparsers.add_parser("new", help="Create a new module specification")
    new_parser.add_argument("spec_file", help="Name of the new module specification file")
    
    # tlc compile
    compile_parser = subparsers.add_parser("compile", help="Compile a module from specification")
    compile_parser.add_argument("spec_file", help="Path to the module specification file")
    
    # tlc test
    test_parser = subparsers.add_parser("test", help="Test a compiled module")
    test_parser.add_argument("spec_file", help="Path to the module specification file")
    
    # tlc run
    run_parser = subparsers.add_parser("run", help="Run a compiled module")
    run_parser.add_argument("spec_file", help="Path to the module specification file")
    run_parser.add_argument("module_args", nargs="*", help="Arguments to pass to the module")
    
    # tlc version
    subparsers.add_parser("version", help="Print the tlc version")
    
    args = parser.parse_args()
    
    if args.command == "new":
        return 0 if create_new_module(args.spec_file) else 1
    elif args.command == "compile":
        return 0 if compile_module(args.spec_file) else 1
    elif args.command == "test":
        return 0 if test_module(args.spec_file) else 1
    elif args.command == "run":
        return 0 if run_module(args.spec_file, args.module_args) else 1
    elif args.command == "version":
        print("tlc version 0.1.0")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())