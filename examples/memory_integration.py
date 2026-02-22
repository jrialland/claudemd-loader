"""
Example demonstrating Claude Code memory integration.

This shows how to load session notes from Claude Code's memory directory.
"""

import shutil
import tempfile
from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


def main() -> None:
    # Create a temporary project
    project_dir = Path(tempfile.mkdtemp(prefix="memory_example_"))

    # Create CLAUDE.md
    (project_dir / "CLAUDE.md").write_text("""# Project Context

## General Guidelines

- Write clear, maintainable code
- Include comprehensive tests
- Document public APIs
""")

    # Simulate Claude Code's memory directory
    memory_dir = Path.home() / ".claude" / "projects" / project_dir.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create MEMORY.md with session notes
        (memory_dir / "MEMORY.md").write_text("""# Session Memory

## Previous Discussions

- User prefers using pathlib over os.path
- Project uses pytest for testing
- Code style enforced by ruff

## Decisions Made

- Use type hints for all functions
- Max line length: 100 characters
- Import organization: stdlib, third-party, local
""")

        print("=" * 70)
        print("Example 1: Loading WITHOUT memory (use_memory=False)")
        print("=" * 70)

        ctx = ClaudeMdLoaderContext(project_dir, use_memory=False)
        result = ctx.load_claudemd()
        print(result)
        print(f"\nTotal length: {len(result)} characters")

        print("\n" + "=" * 70)
        print("Example 2: Loading WITH memory (default behavior)")
        print("=" * 70)

        ctx_with_memory = ClaudeMdLoaderContext(project_dir)  # use_memory=True by default
        result_with_memory = ctx_with_memory.load_claudemd()
        print(result_with_memory)
        print(f"\nTotal length: {len(result_with_memory)} characters")

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"\nWithout memory: {len(result)} characters")
        print(f"With memory:    {len(result_with_memory)} characters")
        print(f"\nMemory adds:    {len(result_with_memory) - len(result)} characters")
        print("\nNotice: Memory content appears BEFORE the main CLAUDE.md content")

    finally:
        # Clean up
        shutil.rmtree(project_dir)
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


if __name__ == "__main__":
    main()
