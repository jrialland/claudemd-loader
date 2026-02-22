"""
Example demonstrating context-aware file loading based on YAML frontmatter.

This shows how the context_files parameter works with YAML frontmatter
to conditionally load only relevant rules for specific files.
"""

import shutil
import tempfile
from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


def create_example_project() -> Path:
    """Create a project with context-specific rules."""
    project_dir = Path(tempfile.mkdtemp(prefix="context_example_"))

    # Create main CLAUDE.md
    (project_dir / "CLAUDE.md").write_text("""# Project Context

## General Guidelines
@general_rules.md

## API-Specific Rules
@api_rules.md

## Frontend-Specific Rules
@frontend_rules.md

## Python-Specific Rules
@python_rules.md
""")

    # General rules - no frontmatter, always included
    (project_dir / "general_rules.md").write_text("""# General Rules

- Write clear, maintainable code
- Include comprehensive tests
- Document public APIs
""")

    # API rules - only for API files
    (project_dir / "api_rules.md").write_text("""---
paths:
  - "src/api/**/*.py"
  - "src/api/**/*.ts"
---
# API Development Rules

- All endpoints must have input validation
- Use standard error response format
- Include rate limiting
- Add OpenAPI documentation
""")

    # Frontend rules - only for frontend files
    (project_dir / "frontend_rules.md").write_text("""---
paths:
  - "src/components/**/*.tsx"
  - "src/components/**/*.jsx"
  - "src/pages/**/*.tsx"
---
# Frontend Development Rules

- Use TypeScript for type safety
- Follow React best practices
- Ensure accessibility (ARIA labels)
- Optimize bundle size
""")

    # Python rules - only for Python files
    (project_dir / "python_rules.md").write_text("""---
paths:
  - "**/*.py"
---
# Python Development Rules

- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for public functions
- Use pytest for testing
""")

    return project_dir


def main() -> None:
    """Demonstrate context-aware loading."""
    project_dir = create_example_project()

    try:
        ctx = ClaudeMdLoaderContext(project_dir)

        print("=" * 70)
        print("Context-Aware File Loading Example")
        print("=" * 70)

        # Example 1: No context files - load everything
        print("\n1. Loading WITHOUT context_files (all rules included):")
        print("-" * 70)
        result = ctx.load_claudemd()
        print(result)
        print(f"\nTotal length: {len(result)} characters")

        # Example 2: Working on an API file
        print("\n" + "=" * 70)
        print("2. Loading for API file: src/api/users.py")
        print("-" * 70)
        result = ctx.load_claudemd(context_files=["src/api/users.py"])
        print(result)
        print("\nNotice: Includes General + API + Python rules, skips Frontend (silently)")

        # Example 3: Working on a frontend component
        print("\n" + "=" * 70)
        print("3. Loading for Frontend file: src/components/Button.tsx")
        print("-" * 70)
        result = ctx.load_claudemd(context_files=["src/components/Button.tsx"])
        print(result)
        print("\nNotice: Includes General + Frontend rules, skips API + Python (silently)")

        # Example 4: Working on multiple files
        print("\n" + "=" * 70)
        print("4. Loading for multiple files: API + Python utils")
        print("-" * 70)
        result = ctx.load_claudemd(context_files=["src/api/handlers.py", "src/utils/helpers.py"])
        print(result)
        print("\nNotice: Includes General + API + Python rules, skips Frontend (silently)")

        # Example 5: Working on a file that matches no specific rules
        print("\n" + "=" * 70)
        print("5. Loading for config file: config.json")
        print("-" * 70)
        result = ctx.load_claudemd(context_files=["config.json"])
        print(result)
        print("\nNotice: Only includes General rules (others silently skipped)")

        print("\n" + "=" * 70)
        print("Summary:")
        print("=" * 70)
        print("""
The context_files parameter allows you to load only the relevant rules
for the files you're currently working on. This is especially useful for:

1. Large projects with many specialized rules
2. Keeping Claude's context focused and relevant
3. Reducing token usage by excluding irrelevant rules
4. Supporting multi-language projects with language-specific rules

Rules without YAML frontmatter are always included (e.g., general_rules.md).
Rules with frontmatter are included only when context_files match their paths.
""")

    finally:
        # Cleanup
        shutil.rmtree(project_dir)


if __name__ == "__main__":
    main()
