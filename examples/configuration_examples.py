"""
Example demonstrating the new configuration options.

This script shows:
1. Custom claudemd_filename
2. Custom max_recursion_depth
3. Handling of missing main file
"""

import shutil
import tempfile
import warnings
from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


def example_custom_filename() -> None:
    """Example using a custom filename instead of CLAUDE.md."""
    print("\n" + "=" * 60)
    print("Example 1: Custom Filename")
    print("=" * 60)

    project_dir = Path(tempfile.mkdtemp(prefix="custom_filename_"))

    try:
        # Create a file with a custom name
        (project_dir / "PROJECT_CONTEXT.md").write_text("""# My Project Context

This is loaded from PROJECT_CONTEXT.md instead of CLAUDE.md!

## Details
- Custom filename support
- Flexible configuration
""")

        # Load using custom filename
        ctx = ClaudeMdLoaderContext(project_dir, claudemd_filename="PROJECT_CONTEXT.md")
        content = ctx.load_claudemd()

        print("\nLoaded content from PROJECT_CONTEXT.md:")
        print(content)

    finally:
        shutil.rmtree(project_dir)


def example_custom_recursion_depth() -> None:
    """Example using a custom maximum recursion depth."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Max Recursion Depth")
    print("=" * 60)

    project_dir = Path(tempfile.mkdtemp(prefix="custom_depth_"))

    try:
        # Create a chain of imports
        num_levels = 5
        for i in range(num_levels):
            file_path = project_dir / f"level{i}.md"
            if i < num_levels - 1:
                file_path.write_text(f"Level {i}\n\n@level{i + 1}.md")
            else:
                file_path.write_text(f"Level {i} (deepest)")

        (project_dir / "CLAUDE.md").write_text("Start\n\n@level0.md")

        # Load with shallow max depth of 2
        print("\nWith max_recursion_depth=2:")
        ctx = ClaudeMdLoaderContext(project_dir, max_recursion_depth=2)
        content = ctx.load_claudemd()
        print(content)

        print("\n" + "-" * 60)

        # Load with deeper max depth of 5
        print("\nWith max_recursion_depth=5:")
        ctx = ClaudeMdLoaderContext(project_dir, max_recursion_depth=5)
        content = ctx.load_claudemd()
        print(content)

    finally:
        shutil.rmtree(project_dir)


def example_missing_main_file() -> None:
    """Example showing warning when main CLAUDE.md file is missing."""
    print("\n" + "=" * 60)
    print("Example 3: Missing Main File Warning")
    print("=" * 60)

    project_dir = Path(tempfile.mkdtemp(prefix="missing_file_"))

    try:
        # Don't create CLAUDE.md

        print("\nAttempting to load non-existent CLAUDE.md:")
        ctx = ClaudeMdLoaderContext(project_dir)

        # Capture the warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            content = ctx.load_claudemd()

            if w:
                print(f"\\nWarning emitted: {w[0].message}")
            print(f"Content returned: '{content}'")

    finally:
        shutil.rmtree(project_dir)


def example_combined() -> None:
    """Example combining custom filename and max depth."""
    print("\n" + "=" * 60)
    print("Example 4: Combined Configuration")
    print("=" * 60)

    project_dir = Path(tempfile.mkdtemp(prefix="combined_"))

    try:
        # Create custom named file with imports
        (project_dir / "doc1.md").write_text("Document 1")
        (project_dir / "doc2.md").write_text("Document 2\\n\\n@doc1.md")

        (project_dir / "MAIN.md").write_text("""# Main Document

@doc2.md

End of main.
""")

        # Use both custom filename and custom max depth
        ctx = ClaudeMdLoaderContext(project_dir, claudemd_filename="MAIN.md", max_recursion_depth=3)
        content = ctx.load_claudemd()

        print("\nLoaded from MAIN.md with max_recursion_depth=3:")
        print(content)

    finally:
        shutil.rmtree(project_dir)


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("ClaudeMdLoaderContext Configuration Examples")
    print("=" * 60)

    example_custom_filename()
    example_custom_recursion_depth()
    example_missing_main_file()
    example_combined()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
