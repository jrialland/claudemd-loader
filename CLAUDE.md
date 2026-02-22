# claudemd-loader Project Context

This project implements the CLAUDE.md file conventions for loading and processing project context.

## Project Overview

@README.md

## Project Configuration

@pyproject.toml

## Development Guidelines

### Python Standards

- **Python Version**: 3.13+
- **Code Quality**: All code must pass `uv run ruff check` before committing
- **Type Safety**: Full type annotations required (enforced by ruff)

### Dependency Management

This project uses **uv** for dependency management:

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --group=lint <package-name>

# Add a test dependency
uv add --group=test <package-name>
```

### Project Structure

```
claudemd-loader/
├── src/
│   └── claudemd_loader/
│       ├── __init__.py
│       └── ctx.py          # Main ClaudeMdLoaderContext implementation
├── tests/
│   ├── __init__.py
│   └── test_claudemd_loader.py
├── examples/
│   └── basic_usage.py
├── CLAUDE.md               # This file
├── README.md               # Project documentation
├── USAGE.md                # Usage examples
└── pyproject.toml          # PEP 517 build configuration
```

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=claudemd_loader --cov-report=html

# Run specific test
uv run pytest tests/test_claudemd_loader.py::test_basic_loading -v

# Run linter
uv run ruff check

# Auto-fix linter issues
uv run ruff check --fix
```

### Test Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names that explain what is being tested
- Use pytest fixtures for common setup
- Test both success and error cases

## Implementation Details

### Project Context Search

CLAUDE.md files are searched in multiple locations (priority order):

1. **Project directory**: `<project_dir>/CLAUDE.md`
2. **User's .claude directory**: `~/.claude/projects/<project-name>/CLAUDE.md`

The project name is derived from the base directory name. The project directory must be an existing directory (validated in `__init__`).

### Memory Integration

Claude Code writes session notes to `~/.claude/projects/<project-name>/memory/MEMORY.md`. When `use_memory=True` (the default):

- First 200 lines of MEMORY.md are loaded
- Content is prepended before CLAUDE.md content
- Missing files are silently ignored
- Enabled by default to integrate seamlessly with Claude Code

### Error Handling

- Gracefully handle missing files (emit Python warning AND insert HTML comment)
- Detect and prevent circular imports (insert HTML comment in output)
- Enforce maximum recursion depth (insert HTML comment at limit)
- Provide helpful error messages via warnings and HTML comments

### Path Handling

- Use `pathlib.Path` for all file operations
- Always resolve paths to absolute paths
- Support Windows and Unix path separators
- Handle home directory expansion (`~/`)

### Import Processing

The library processes `@path/to/file` import syntax:

1. **Code Block Detection**: Skip imports in ``` code blocks and `inline code`
2. **Path Resolution**: Resolve relative to current file's directory
3. **Circular Detection**: Track loaded files to prevent infinite loops
4. **Depth Limiting**: Max 5 levels of nested imports (configurable)
5. **Extension Auto-detection**: Try `.md`, `.txt`, `.json` if no extension

### YAML Frontmatter & Context-Aware Loading

Files may include optional YAML frontmatter for conditional loading:

```yaml
---
paths:
  - "src/api/**/*.py"
  - "tests/api/**/*.py"
---
```

When `context_files` is passed to `load_claudemd()`, files are filtered based on frontmatter `paths` patterns. Files without frontmatter are always included. See [USAGE.md](USAGE.md) for complete details and examples.

## Contributing

When contributing to this project:

1. Ensure all tests pass: `uv run pytest tests/ -v`
2. Ensure linter passes: `uv run ruff check`
3. Add tests for new features
4. Update documentation (README.md, USAGE.md) as needed
5. Keep the implementation aligned with the CLAUDE.md specification

## Specification Compliance

This library implements the CLAUDE.md specification as documented in:
- [The Ultimate Guide to CLAUDE.md](https://www.buildcamp.io/guides/the-ultimate-guide-to-claudemd)
- [Notes on CLAUDE.md Structure and Best Practices](https://callmephilip.com/posts/notes-on-claude-md-structure-and-best-practices/)

Key specifications:
- Import syntax: `@path/to/file`
- Code block exemption: imports in code blocks are not processed
- Recursion limit: 5 levels deep
- YAML frontmatter: optional metadata at file start
- Circular import prevention
