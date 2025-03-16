**Question**: What should happen if the input file doesn't exist?
  **Assumption**: Exit with error code 1 and print error message to stderr

**Question**: What should happen if the output directory can't be created?
  **Assumption**: Exit with error code 1 and print error message to stderr

**Question**: What should happen if the output file already exists?
  **Assumption**: Overwrite the existing file

**Question**: Should there be a --help or -h option?
  **Assumption**: Yes, following standard CLI conventions

**Question**: Should there be a --version option?
  **Assumption**: Yes, following standard CLI conventions

**Question**: What other commands besides "compile" should be supported?
  **Assumption**: None for now - the spec only mentions compile

**Question**: Should there be a way to specify a different output directory than 'tlc/'?
  **Assumption**: No - the spec explicitly states output goes to tlc/ directory

**Question**: What should happen if the markdown file is invalid?
  **Assumption**: Exit with error code 1 and print error message to stderr

**Question**: Should there be any verbosity options (-v, --verbose)?
  **Assumption**: No - not mentioned in spec and not necessary for core functionality

**Question**: How should file permission errors be handled?
  **Assumption**: Exit with error code 1 and print error message to stderr