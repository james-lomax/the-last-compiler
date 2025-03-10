# the_last_compiler.py

## Inputs

- A markdown file named my-module-name.md with a specification for a python module

## Outputs

- A python module at tlc/${my_module_name}.py
- An updated uv pyproject.toml file

## Implementation

- Write a python module called the_last_compiler.py that uses an LLM to “compile” any markdown document with a specification describing a python module, so long as it is well enough defined
- Module supports sub-commands:
    - tlc new my-module-name.md -- Create a new template module spec file
    - tlc compile my-module-name.md -- Compile the module to its python module
    - tlc test my-module-name.md -- (Compile and then) Run the tests for the module if they exist
    - tlc run my-module-name.md {args} -- (Compile and then) Run the module with the given args
    - tlc version -- Prints "tlc version 0.1.0"

### General instructions

- The the_last_compiler.py python module must have a main method.
- The prompts will be defined using jinja2 templates at the top of the the_last_compiler.py file.
- Do not over-comment. Lines of code should be self-documenting.
- Add tlc to the pyproject.toml file with the tlc tool - users can invoke with the command `tlc`
- When you have finished implementing the module, stop - claude code can exit. 
- This script should be sufficient to implement the module, you must only add the the_last_compiler.py module, and edit the pyproject.toml file.
- Markdown module files should be named with hyphens, python module files should be named with underscores.

Update the pyproject.toml uv file format like this:

```python
[project]
...

[project.scripts]
{{ my_module_name }} = tlc.{{ my_module_name }}:main"
```

This allows us to run `uv run {{ my_module_name }}`

In the case of this module you should add the script:

```python
[project.scripts]
tlc = tlc.the_last_compiler:main"
```

This allows us to run `uv run tlc`

### tlc compile my-module-name.md

- Use claude code to implement the changes using a prompt
- Include the following points in the prompt:
    - "Read the spec and consider the weaknesses of the spec: is it well defined enough to implement in a single python module? Are there any important unanswered questions? Are there any things you don’t know how to do? Are any of these blockers to proceeding?"
    - "If no, Stop, and summarise why you cannot yet implement this spec as an error."
    - "If yes, describe what we need to do to implement this module, then implement it."
    - The module is always tlc/{my_module_name}.py
    - If a test strategy is specified, implement it in tlc/tests/test_{module_name}.py
    - update pyproject.toml to add the new module entry point (provide more info in the prompt from below)
    - This script should be sufficient to implement the module, you must only add the {my_module_name}.py module, and edit the pyproject.toml file.
- Render the prompt to bin/prompt/the_last_compiler.md
- The prompt will be passed to claude code by running the command `f'claude "Follow the instructions in bin/prompt/the_last_compiler.md"'` - quotes will have to be escaped in the command - make a function called "run_claude_code" which runs this command. This function should use subprocess.call in shell mode so we can see it's output.
- Do not write a prompt chain, just use claude code.

### tlc new my-module-name.md

Create a new markdown file named my-module-name.md in the current directorty with the following template contents:

```markdown
# {my-module-name}.py

## Inputs

TODO define inputs

## Outputs

TODO define outputs

## Implementation

TODO define implementation. Be really specific about what code to write, and where to write it.

