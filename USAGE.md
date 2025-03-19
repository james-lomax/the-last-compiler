# The last compiler

The last compiler helps you create tools quickly by compile markdown specifications of python modules into python, and adding some boilerplate to easily install the project as a tool with `uvx`

## Getting started

Create a new tool from a template with:

```
tlc init tool-name
```

This will create a directory called `tool-name` with the pre-requisites in the following structure:
```
- tool-name/
	- USAGE.md
	- pyproject.toml
	- tool-name/
		- __main__.py
		- my-module.md
```