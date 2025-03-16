#!/usr/bin/env python3
"""
tlc.py - The Last Compiler CLI

A compiler of markdown specifications into code.
This module implements the CLI for all the commands in this project.
"""

import sys
from pathlib import Path
from tlc.compile_spec import compile_spec

def main():
    """Main CLI entrypoint for tlc"""
    if len(sys.argv) < 2:
        print("Usage: tlc <command> [args...]")
        print("\nAvailable commands:")
        print("  compile path/to/module-name.md  Compile markdown spec to Python module")
        sys.exit(1)

    command = sys.argv[1]
    
    if command == "compile":
        if len(sys.argv) != 3:
            print("Usage: tlc compile path/to/module-name.md")
            sys.exit(1)
            
        spec_path = sys.argv[2]
        success = compile_spec(spec_path)
        
        if success:
            print("Compilation succeeded.")
            sys.exit(0)
        else:
            print("Compilation failed or produced code with issues.")
            sys.exit(1)
    elif command == "version":
        print(f"tlc version 0.3.0")
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 