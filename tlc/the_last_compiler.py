#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from jinja2 import Template

# Jinja2 templates for prompts
COMPILE_PROMPT_TEMPLATE = """
# Implementation Task for {{ module_name_py }}

Please read the following specification and implement the requested Python module.

## Specification
{{ spec_content }}

## Implementation Guidelines

1. Read the spec and consider the weaknesses of the spec: is it well defined enough to implement in a single python module? Are there any important unanswered questions? Are there any things you don't know how to do? Are any of these blockers to proceeding?

2. If no, Stop, and summarise why you cannot yet implement this spec as an error.

3. If yes, describe what we need to do to implement this module, then implement it.

Important notes:
- The module should be implemented as tlc/{{ module_name_py }}.py
- If a test strategy is specified, implement it in tlc/tests/test_{{ module_name_py }}.py
- Update pyproject.toml to add the new module entry point by adding the following to the [project.scripts] section:
  {{ module_name_md }} = "tlc.{{ module_name_py }}:main"

This script should be sufficient to implement the module, you must only add the {{ module_name_py }}.py module, and edit the pyproject.toml file.
"""

NEW_MODULE_TEMPLATE = """# {module_name}.py

## Inputs

TODO define inputs

## Outputs

TODO define outputs

## Implementation

TODO define implementation. Be really specific about what code to write, and where to write it.
"""

def md_to_py_module_name(md_filename):
    """Convert markdown filename to Python module name."""
    base_name = os.path.basename(md_filename)
    module_name = os.path.splitext(base_name)[0]
    return module_name.replace('-', '_')

def ensure_dir_exists(dir_path):
    """Ensure directory exists, create if it doesn't."""
    Path(dir_path).mkdir(parents=True, exist_ok=True)

def run_claude_code(prompt_path):
    """Run Claude Code with the given prompt file."""
    cmd = f'claude "Follow the instructions in {prompt_path}"'
    return subprocess.call(cmd, shell=True)

def cmd_new(args):
    """Create a new module spec template."""
    if not args.module_spec.endswith('.md'):
        print(f"Error: Module spec file must end with .md: {args.module_spec}")
        return 1
    
    if os.path.exists(args.module_spec):
        print(f"Error: {args.module_spec} already exists")
        return 1

    module_name = os.path.splitext(os.path.basename(args.module_spec))[0]
    content = NEW_MODULE_TEMPLATE.format(module_name=module_name)
    
    with open(args.module_spec, 'w') as f:
        f.write(content)
    
    print(f"Created new module spec: {args.module_spec}")
    return 0

def cmd_compile(args):
    """Compile a module spec to Python."""
    if not os.path.exists(args.module_spec):
        print(f"Error: Module spec file not found: {args.module_spec}")
        return 1
    
    module_name_md = os.path.splitext(os.path.basename(args.module_spec))[0]
    module_name_py = md_to_py_module_name(args.module_spec)
    
    # Delete existing module if it exists
    module_path = f"tlc/{module_name_py}.py"
    if os.path.exists(module_path):
        os.remove(module_path)
        print(f"Removed existing module: {module_path}")
    
    # Read the module spec
    with open(args.module_spec, 'r') as f:
        spec_content = f.read()
    
    # Create prompt directory if it doesn't exist
    ensure_dir_exists("bin/prompt")
    
    # Render the prompt template
    template = Template(COMPILE_PROMPT_TEMPLATE)
    prompt = template.render(
        module_name_md=module_name_md,
        module_name_py=module_name_py,
        spec_content=spec_content
    )
    
    # Write the prompt to a file
    prompt_path = "bin/prompt/the_last_compiler.md"
    with open(prompt_path, 'w') as f:
        f.write(prompt)
    
    # Run Claude Code
    print(f"Running Claude Code to compile {args.module_spec}...")
    return run_claude_code(prompt_path)

def cmd_test(args):
    """Compile and test a module."""
    result = cmd_compile(args)
    if result != 0:
        return result
    
    module_name_py = md_to_py_module_name(args.module_spec)
    test_module = f"tlc.tests.test_{module_name_py}"
    
    print(f"Running tests for {module_name_py}...")
    cmd = f"python -m unittest {test_module}"
    return subprocess.call(cmd, shell=True)

def cmd_run(args):
    """Compile and run a module with given args."""
    # result = cmd_compile(args)
    # if result != 0:
    #     return result
    
    module_name_md = os.path.splitext(os.path.basename(args.module_spec))[0]
    module_args = args.args if args.args else []
    
    print(f"Running {module_name_md} with args: {module_args}")
    cmd = ["uv", "run", module_name_md] + module_args
    return subprocess.call(cmd)

def cmd_version(_):
    """Print the version."""
    print("tlc version 0.2.0")
    return 0

def main():
    parser = argparse.ArgumentParser(description="The Last Compiler")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # new command
    new_parser = subparsers.add_parser("new", help="Create a new module spec template")
    new_parser.add_argument("module_spec", help="Module spec filename (*.md)")
    
    # compile command
    compile_parser = subparsers.add_parser("compile", help="Compile a module spec to Python")
    compile_parser.add_argument("module_spec", help="Module spec filename (*.md)")
    
    # test command
    test_parser = subparsers.add_parser("test", help="Compile and test a module")
    test_parser.add_argument("module_spec", help="Module spec filename (*.md)")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Compile and run a module")
    run_parser.add_argument("module_spec", help="Module spec filename (*.md)")
    run_parser.add_argument("args", nargs="*", help="Arguments to pass to the module")
    
    # version command
    subparsers.add_parser("version", help="Print the version")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Call the appropriate command function
    if args.command == "new":
        return cmd_new(args)
    elif args.command == "compile":
        return cmd_compile(args)
    elif args.command == "test":
        return cmd_test(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "version":
        return cmd_version(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())