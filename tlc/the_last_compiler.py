#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path
from jinja2 import Template

# Jinja2 template for the Claude Code prompt
CLAUDE_PROMPT_TEMPLATE = """
Read the spec and consider the weaknesses of spec: is it well defined enough to implement in a single python module? Are there any important unanswered questions? Are there any things you don't know how to do? Are any of these blockers to proceeding?

If no, Stop, and summarise why you cannot yet implement this spec as an error.

If yes, describe what we need to do to implement this module, then implement it.

The module is always tlc/{{ module_name }}.py

{% if test_strategy %}
If a test strategy is specified, implement it in tlc/tests/test_{{ module_name }}.py
{% endif %}

update pyproject.toml to add the new module entry

This script should be sufficient to implement the module, you must only add the {{ module_name }}.py module, and edit the pyproject.toml file.
"""

def parse_args():
    parser = argparse.ArgumentParser(description='The Last Compiler - Compile markdown specs into Python modules')
    parser.add_argument('spec_file', type=str, help='Path to markdown specification file')
    return parser.parse_args()

def extract_module_name(spec_content):
    """Extract module name from the spec content."""
    # Assuming the module name is defined in the first line or can be derived from the filename
    first_line = spec_content.strip().split('\n')[0]
    if first_line.startswith('# '):
        # Extract from markdown title, e.g., "# my_module.py" -> "my_module"
        module_name = first_line[2:].strip()
        if module_name.endswith('.py'):
            module_name = module_name[:-3]
        return module_name
    return None

def generate_prompt(spec_content):
    """Generate the prompt for Claude Code based on the spec content."""
    module_name = extract_module_name(spec_content)
    if not module_name:
        raise ValueError("Could not extract module name from spec content")
    
    # Check if test strategy is mentioned in the spec
    test_strategy = "test" in spec_content.lower()
    
    # Render the prompt template
    template = Template(CLAUDE_PROMPT_TEMPLATE)
    prompt = template.render(module_name=module_name, test_strategy=test_strategy)
    
    # Add the spec content to the prompt
    full_prompt = f"{prompt}\n\nHere is the specification:\n\n{spec_content}"
    
    return full_prompt, module_name

def save_prompt(prompt, output_path):
    """Save the prompt to a file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(prompt)

def update_pyproject_toml(module_name):
    """Update the pyproject.toml file with the new module entry."""
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        raise FileNotFoundError(f"Could not find {pyproject_path}")
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Check if the module is already in the scripts section
    script_entry = f"{module_name} = \"tlc.{module_name}:main\""
    if script_entry in content:
        print(f"Script entry for {module_name} already exists in pyproject.toml")
        return
    
    # Add the new script entry
    if "[project.scripts]" in content:
        # Find the scripts section and add the new entry
        lines = content.split('\n')
        scripts_index = lines.index("[project.scripts]")
        
        # Find where the scripts section ends
        end_index = len(lines)
        for i in range(scripts_index + 1, len(lines)):
            if lines[i].strip() and lines[i].startswith('['):
                end_index = i
                break
        
        # Insert the new script entry
        lines.insert(end_index, f"{module_name} = \"tlc.{module_name}:main\"")
        updated_content = '\n'.join(lines)
    else:
        # If there's no scripts section, add it
        updated_content = f"{content.strip()}\n\n[project.scripts]\n{module_name} = \"tlc.{module_name}:main\"\n"
    
    with open(pyproject_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated pyproject.toml with {module_name} script entry")

def run_claude_code(prompt_path):
    """Run Claude Code with the generated prompt."""
    escaped_prompt = f"Follow the instructions in {prompt_path}".replace('"', '\\"')
    command = f'claude "{escaped_prompt}"'
    
    print(f"Running command: {command}")
    
    # Use a simpler approach that directly connects to the terminal
    try:
        # This will connect the process directly to the user's terminal
        return subprocess.run(command, shell=True, check=False).returncode
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running Claude: {e}", file=sys.stderr)
        return 1

def main():
    args = parse_args()
    spec_file = args.spec_file
    
    if not os.path.exists(spec_file):
        print(f"Error: Specification file {spec_file} does not exist")
        sys.exit(1)
    
    with open(spec_file, 'r') as f:
        spec_content = f.read()
    
    try:
        prompt, module_name = generate_prompt(spec_content)
        prompt_path = os.path.join('bin', 'prompt', 'the_last_compiler.md')
        save_prompt(prompt, prompt_path)
        
        print(f"Generated prompt for {module_name}")
        print(f"Running Claude Code to implement the module...")
        
        # Run Claude Code with the generated prompt
        exit_code = run_claude_code(prompt_path)
        
        if exit_code != 0:
            print(f"Error: Claude Code exited with code {exit_code}")
            sys.exit(exit_code)
        
        # Update pyproject.toml with the new module entry
        update_pyproject_toml(module_name)
        
        print(f"Successfully compiled {spec_file} to tlc/{module_name}.py")
        print(f"You can now run the module with: uv run {module_name}")
        
    except Exception as e:
        # Don't wrap exceptions, show the full stack trace
        raise

if __name__ == "__main__":
    main()