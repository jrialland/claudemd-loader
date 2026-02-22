"""
Example demonstrating multi-file CLAUDE.md loading.

This example shows how claudemd-loader loads multiple CLAUDE.md files
from conventional locations in a specific order.
"""

from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


# Suppose you have this directory structure:
#
# ~/.claude/CLAUDE.md                               # User global (all projects)
# ~/.claude/projects/myproject/CLAUDE.md           # Project-specific (user level)
# ~/code/myproject/CLAUDE.md                       # Project root
# ~/code/myproject/.claude/CLAUDE.md              # Project .claude directory
# ~/code/myproject/.claude/rules/api.md           # Scoped rules for API code
# ~/code/myproject/.claude/rules/database.md      # Scoped rules for database
# ~/code/myproject/CLAUDE.local.md                # Local personal overrides

# All of these files are loaded in order and concatenated:

print("Multi-file Loading Example")
print("=" * 50)
print()

# Example 1: Load from project directory
print("Example 1: Conventional file loading")
print("-" * 50)

# Create a context
project_dir = Path(__file__).parent.parent.resolve()
ctx = ClaudeMdLoaderContext(project_dir)

# This will load ALL existing files in order:
# 1. ~/.claude/CLAUDE.md (if exists)
# 2. ~/.claude/projects/<project>/CLAUDE.md (if exists)
# 3. ./CLAUDE.md (if exists)
# 4. ./.claude/CLAUDE.md (if exists)
# 5. ./.claude/rules/**/*.md (all .md files recursively, sorted)
# 6. ./CLAUDE.local.md (if exists)

content = ctx.load_claudemd()
print(f"Loaded {len(content)} characters from conventional locations")
print()

# Example 2: Load with extra files
print("Example 2: Loading with extra files")
print("-" * 50)

# You can also specify additional files to load
# These are loaded AFTER all conventional files
extra_files = [
    "docs/api-guidelines.md",
    "docs/coding-standards.md",
]

# Note: This example won't find these files unless they exist,
# but demonstrates the API
content_with_extra = ctx.load_claudemd(extra_claude_files=extra_files)
print(f"With extra files specified: {len(content_with_extra)} characters")
print()

# Example 3: Typical use case - session context building
print("Example 3: Building session context")
print("-" * 50)
print("""
Typical workflow:

1. User global CLAUDE.md (~/.claude/CLAUDE.md)
   - Contains your personal coding standards
   - Coding style preferences
   - Common tools/libraries you prefer

2. Project-specific user CLAUDE.md (~/.claude/projects/myproject/CLAUDE.md)
   - Project-specific instructions
   - Architecture notes
   - Team conventions

3. Project root CLAUDE.md (./CLAUDE.md)
   - Checked into git
   - Shared with team
   - Project-wide context

4. Project .claude directory (./.claude/CLAUDE.md)
   - Also checked into git
   - Alternative location for project context

5. Project rules (./.claude/rules/**/*.md)
   - Modular rules organized by topic
   - Supports frontmatter for conditional loading
   - Examples: api/, database/, frontend/
   - Loaded recursively in alphabetical order

6. Local personal CLAUDE.md (./CLAUDE.local.md)
   - NOT checked into git (auto-ignored)
   - Your personal notes for this project
   - Local overrides

7. Extra files (via parameter)
   - Documents you want included for this specific session
   - Domain-specific guidelines
   - API documentation

All combined into one context string for the AI session!
""")
