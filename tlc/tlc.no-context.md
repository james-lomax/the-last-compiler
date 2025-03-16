# Dependencies

## Interface from compile-spec.md

compile-spec turns markdown module specification files into code in a low-context way.


Usage:


```python
compile_spec("path/to/module-name.md")
```

This reads the file at `path/to/module-name.md` and writes a python module to `path/to/tlc/module_name.py`. compile_spec handles determining the output target file, reading and writing files and creating directories. The output files are always created in a `tlc` directory adjacent to the input specification file.


# # tlc.py


the-last-compiler: a compiler of markdown specifications into code


This module implements the CLI for all the commands in this project.


## ## Usage


Compile path/to/module-name.md to tlc/path/to/module_name.py


```
tlc compile path/to/module-name.md
```

## ## Implementation


Use [[compile-spec]] to do `tlc compile`
