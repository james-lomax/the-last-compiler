## Usage

```
tlc install tool-name
```
Installs the tlc project ([[tlc-project]])

## Implementation
Just calls:
```bash
tlc build tool-name
uv uninstall tool-name
uv install tool-name
```

