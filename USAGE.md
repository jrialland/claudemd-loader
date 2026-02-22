# Usage Examples

## Basic Usage

```python
from claudemd_loader import ClaudeMdLoaderContext
from pathlib import Path

# Initialize the context with your project directory
ctx = ClaudeMdLoaderContext("/path/to/your/project")

# Load the default CLAUDE.md file
content = ctx.load_claudemd()
print(content)
```

## Multi-File Loading

The library automatically loads and concatenates CLAUDE.md files from multiple conventional locations in a specific order. This allows you to layer context from user-wide preferences down to project-specific details.

### Loading Order

All existing files are loaded and concatenated in this order:

1. **User global**: `~/.claude/CLAUDE.md`
2. **Project-specific user**: `~/.claude/projects/<project-name>/CLAUDE.md`
3. **Project root**: `<project_dir>/CLAUDE.md`
4. **Project .claude directory**: `<project_dir>/.claude/CLAUDE.md`
5. **Project rules**: `<project_dir>/.claude/rules/**/*.md` (loaded recursively in alphabetical order)
6. **Local personal**: `<project_dir>/CLAUDE.local.md`
7. **Extra files**: Specified via `extra_claude_files` parameter

**Note**: Rule files in `.claude/rules/` support YAML frontmatter with `paths:` patterns for conditional loading.

```python
from claudemd_loader import ClaudeMdLoaderContext

# Project name will be "myproject" (from directory name)
ctx = ClaudeMdLoaderContext("/home/user/workspace/myproject")

# Loads ALL existing files in the order above
content = ctx.load_claudemd()

# Optionally load additional files after conventional ones
extra_content = ctx.load_claudemd(
    extra_claude_files=["docs/api-guide.md", "docs/style-guide.md"]
)
```

This allows you to maintain:
- **User global**: Your personal coding standards for all projects
- **Project-specific user**: Project notes stored at user level
- **Project root**: Team-shared project context (version controlled)
- **Project .claude**: Alternative location for shared context
- **Project rules**: Modular, scoped rules organized by topic (e.g., `api/`, `database/`, `frontend/`)
- **Local personal**: Your private notes (add to `.gitignore`)
- **Extra files**: Session-specific documentation

All files are concatenated with double newlines between them.

## Custom Configuration

```python
# Use a custom filename instead of CLAUDE.md
ctx = ClaudeMdLoaderContext(
    "/path/to/your/project",
    claudemd_filename="CONTEXT.md"
)

# Customize the maximum recursion depth (default is 5)
ctx = ClaudeMdLoaderContext(
    "/path/to/your/project",
    max_recursion_depth=10
)

# Both together
ctx = ClaudeMdLoaderContext(
    "/path/to/your/project",
    claudemd_filename="MY_CONTEXT.md",
    max_recursion_depth=3
)
content = ctx.load_claudemd()
```

## Memory Integration

Load session notes from Claude Code's memory directory:

```python
from claudemd_loader import ClaudeMdLoaderContext

# Memory loading is enabled by default
ctx = ClaudeMdLoaderContext("/path/to/your/project")
content = ctx.load_claudemd()

# Explicitly disable it if needed
ctx = ClaudeMdLoaderContext("/path/to/your/project", use_memory=False)

# Memory can be combined with other options
ctx = ClaudeMdLoaderContext(
    "/path/to/your/project",
    claudemd_filename="CONTEXT.md",
    max_recursion_depth=10,
    use_memory=True  # True by default, shown here for clarity
)
content = ctx.load_claudemd()
```

**How it works:**

- Loads from `~/.claude/projects/<project-name>/memory/MEMORY.md`
- Only first 200 lines are loaded
- Memory content is prepended before the main CLAUDE.md content
- Missing MEMORY.md files are silently ignored
- Enabled by default (set `use_memory=False` to disable)

This integrates with Claude Code's automatic note-taking feature, preserving session context across conversations.

## Context Files Parameter

The `context_files` parameter enables **conditional loading** based on YAML frontmatter in your context files. This is useful for large projects with specialized rules that should only apply to specific files.

### How It Works

1. **No context_files**: All files are loaded (default behavior)
2. **With context_files**: Only files matching the frontmatter `paths` patterns are included
3. **No frontmatter**: Files without YAML frontmatter are always included

### Example

```python
ctx = ClaudeMdLoaderContext("/path/to/your/project")

# Load rules relevant to specific files you're working on
content = ctx.load_claudemd(context_files=[
    "src/api/users.py",
    "src/api/handlers.py"
])
```

### YAML Frontmatter Format

```markdown
---
paths:
  - "src/api/**/*.py"
  - "src/api/**/*.ts"
---
# API Rules

All API endpoints must include input validation.
```

### Pattern Matching

Supports glob patterns:
- `*.py` - All Python files in current directory
- `**/*.py` - All Python files recursively
- `src/**/*.ts` - All TypeScript files under src/
- `tests/**/*` - All files in tests/

### Use Cases

1. **Multi-language projects**: Load only Python rules when editing `.py` files
2. **Large codebases**: Include only relevant subsystem rules
3. **Token optimization**: Reduce context size by excluding irrelevant rules
4. **Role-based rules**: Different rules for API, frontend, database layers

**Note**: Files that don't match the `paths` patterns are silently skipped (empty content returned), keeping your output clean and focused.

See [examples/context_aware_loading.py](examples/context_aware_loading.py) for a complete demonstration.

## Example Project Structure

```
my-project/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── api.md
│   └── setup.md
└── src/
    └── main.py
```

### CLAUDE.md Example

```markdown
# Project Context

## Overview
@README.md

## API Documentation
@docs/api.md

## Setup Instructions
@docs/setup.md
```

## Features

### 1. Import Resolution
- **Relative paths**: `@README` or `@README.md`
- **Subdirectories**: `@docs/guide.md`
- **Home directory**: `@~/.claude/global-rules.md`
- **Auto-extension**: Files without extensions will try `.md`, `.txt`, `.json`

### 2. Code Block Protection
Imports inside code blocks or inline code are **not** processed:

```markdown
# Example

This will be imported: @README.md

But this won't:
```bash
# This is just documentation
@README.md
```

And neither will this: `@README.md`
```

### 3. Circular Import Detection
The library automatically detects and prevents infinite loops:

```python
# a.md contains: @b.md
# b.md contains: @a.md

ctx = ClaudeMdLoaderContext("/path/to/project")
# Load the main CLAUDE.md that imports a.md
content = ctx.load_claudemd()
# Result will include a comment: "<!-- Circular import detected: ... -->"
```

### 4. Maximum Recursion Depth
Imports are limited to a configurable depth (default 5 levels) to prevent excessive nesting:

```python
# Use a shallower recursion depth
ctx = ClaudeMdLoaderContext("/path/to/project", max_recursion_depth=3)
content = ctx.load_claudemd()
# Will show: <!-- Max recursion depth (3) exceeded for ... --> if exceeded
```

### 5. YAML Frontmatter Support
Files can include optional YAML frontmatter:

```markdown
---
paths:
  - "src/**/*.py"
---
# Python-specific Rules

All Python code must follow PEP 8.
```

The frontmatter is parsed but removed from the final output.

### 6. Proper Content Concatenation

The library automatically ensures that imported files are properly separated by adding a newline to file content that doesn't already end with one. This prevents content from different files from running together.

## Error Handling

The library handles various error conditions gracefully:

- **Missing files**: Emits a Python `UserWarning` AND inserts `<!-- File not found: path/to/file -->` in output
- **Circular imports**: Inserts `<!-- Circular import detected: path/to/file -->`
- **Max recursion**: Inserts `<!-- Max recursion depth (N) exceeded for path/to/file -->` where N is the configured limit
- **Skipped files**: Files not matching `context_files` patterns are silently skipped (empty string returned)

Example of handling missing files:

```python
import warnings
from claudemd_loader import ClaudeMdLoaderContext

# Capture warnings to handle them programmatically
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    ctx = ClaudeMdLoaderContext("/path/to/project")
    content = ctx.load_claudemd()
    
    # Check if any files were missing
    for warning in w:
        if "File not found" in str(warning.message):
            print(f"Warning: {warning.message}")
    
    # The output will also contain HTML comments for missing files
    if "<!-- File not found" in content:
        print("Some files were not found (see HTML comments in output)")
```

## Chunking / RAG Support

For retrieval-augmented generation (RAG) applications, you often need to split context into separate chunks rather than loading it all as one large file. The `load_claudemd_chunks` method supports this use case.

It returns a generator that yields tuples of `(file_path, text_chunk, start_line, end_line)`.

### Basic Usage

```python
from claudemd_loader import ClaudeMdLoaderContext

ctx = ClaudeMdLoaderContext(".")

# Chunk all loaded files with default size (1000 chars) and no overlap
for filepath, chunk, start, end in ctx.load_claudemd_chunks():
    print(f"File: {filepath} ({start}-{end})")
    print(f"Content: {chunk[:50]}...")
```

### Advanced Configuration

You can configure the chunk size and overlap:

```python
# Create 500-character chunks with 50-character overlap
chunks = ctx.load_claudemd_chunks(
    chunk_size=500,
    chunk_overlap=50
)

for _, text, _, _ in chunks:
    # Process overlapping chunks...
    pass
```

The method accepts the same `context_files` parameter as `load_claudemd` to filter which files are loaded based on their frontmatter rules.

