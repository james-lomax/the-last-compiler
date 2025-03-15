# compile_spec.py

compile-spec turns markdown module specification files into code in a low-context way.

Usage:

```
compile-spec <module-name.md>
```

## Implementation

The compile step is always preceded by the sanity check step, using [[sanity-check-spec]]. This preprocesses the specification, produces a Q&A, and fails if the spec is not ready to implement.

### System prompt

This system prompt is used in all the following chat prompt steps.

```jinja2
You are a highly skilled Python software engineer. Your job is to read module specifications that describe the implementation of a Python module and turn it into clean, working code.

The specification files should generally define:
- Dependencies on other modules (named like [[path/to/module]])
- The interface this module exposes and how it is used
- the inputs and outputs of the program
- the command arguments of the program
- how the program is implemented

Sometimes specifications may include pseudo-code, intended to make it clear about how a bit of the program should be implemented.
```

### One shot code generation prompt step

When the spec is ready, `compile-spec` performs code generation one-shot - a single code generation prompt is used to produce the output file, which is saved to the code target file in the `tlc/` directory.

```jinja2
Consider the following specification:

====== BEGIN {module_name} specification ======
{no_context_spec}
====== END {module_name} specification ======

We have reviewed this specification, and discussed some clarifications in this Q&A:

{q_and_a}

The specification is ready to implement in {module_code_target}. Write the code for this module. Do not write anything else, just the code.
```

### Code review step

After producing the output code file, we perform a code review to check the implementation worked well.

First we think about the code

```jinja2
Consider the following specification:

====== BEGIN {module_name} specification ======
{no_context_spec}
====== END {module_name} specification ======

Here is our implementation:

====== BEGIN {module_code_target} implementation ======
{code}
====== END {module_code_target} implementation ======

Review this implementation. Is it complete? Is it valid code? Does it meet our specifications expectations?
```

AI responds with some thoughts, and then:

```jinja2
Answering only yes or no, is this implementation ready to use?
```

If response is "yes", stop, printing "Compile succeeded"

If response is "no", ask a follow up:

```jinja2
Summarise why this implementation is not ready. Briefly give some suggestions as to how we might improve the specification to fix this.
```
