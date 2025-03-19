- Fix intermediates - should be internal files (.tlc/)
- Support for more caching - check if the input file has changed, as well as through the dependency structure
	- Maintain an internal JSON structure of files, the last completed compile hash.
- commands dont need .md on the end
- Apply principals of [SOLID](https://en.wikipedia.org/wiki/SOLID)
	- Separate `module.py` and `module_impl.py` - generate using using usage/interface section and all sections respectively (saves recompiling some bits)
	- Stipulate SOLID requirements to module reviewer. "Would this module adhere to the single-responsibility principal?" etc
- rebuild tlc using tlc and copy paste.
- Implement tlc run
- Support for referencing python modules
- `tlc [init|check|compile|build|run|version]` command

## Common uv tool structure

```bash
tlc run tool-name/command

# Calls
tlc compile tool-name/command.md
pushd
uv run python tool-name/tlc/command.py
```

```
tlc install tool-name
```

Calls:
```
tlc build tool-name
uv install tool-name
```

### more stuff from before

- Fix compile output
- Perform linting check on code...
- Cache steps
	- Hash of the most recent verified sane input file
		- Skip sanity check if we hit
	- Hash of the most recent successful output file
		- Skip compile if we hit
- `tlc [init|check|compile|build|version]` command
	- `tlc init` -- calls uv init, and writes some files of its own
- Move Q&A into a `# FAQ` section at the end of the document to make maintenance easier?
- Fix rate limiting
	- Need swappable back-end
	- Catch exceptions with back-off
	- Try a different backend ?
	- Review what messages we send...
		- Make a markdown rendering of the logs for review....
	- I think this re-prompting stuff is really inefficient... need kv caching?
- `tlc sync` -- reads changes in implementation, describes them in a `# Additional notes for code generation` section
- Support @`code_reference` 
	- @`path/to/file.py` to reference implementation
	- Any code file references will require that code file to be built first and added to the input prompt, so the compile will refused to run on a file if the source file dependency is out of date
	- Warnings or errors from sanity check if a symbol isn't defined in the project
- Intermediate format idea:
	- Break down into a list of functionalities that need to be implemented
	- Separate build sub-step for each
		- Each sub-step gets described in more detail, include the inputs and outputs from other sub-steps
		- Each sub-step gets code generated and then split into:
			- Imports
			- Constants
			- dataclasses
			- classes
		- After combining them in one file, we would have to do a fix pass with the model
	- Keeps code small
- New file structure:
	- Arrange your specs into a module, every module with specs gets a tlc directory to contain generated outputs
	- Should we break down sub-steps into files?
- Cursor rules for writing spec (added with tlc init)


## Compiler is an agent idea

Is the compiler actually an agent with some very specific tools:  
  
- sanity check  
- compile  
- read old files  
- write to new ones  
- create UV unit  
- run commands in the workspace or tell us why they don't work  
- list changes files

Implementation:
- Agent is briefed on the current state of the directory with a breakdown of what files need compiling, whether uv is initialised, if the cursor rules are up to date
- Could have an AI chat window in Obsidian... maybe I can use an existing chat plugin, add an MCP, then we can do file referencing as well..
