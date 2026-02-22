"""
Example demonstrating the claudemd-loader library.

This script creates a sample project structure and shows how to use
the ClaudeMdLoaderContext to load and process CLAUDE.md files.
"""

import shutil
import tempfile
from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


def create_example_project() -> Path:
    """Create a temporary example project."""
    # Create temporary directory
    project_dir = Path(tempfile.mkdtemp(prefix="claudemd_example_"))

    # Create main CLAUDE.md
    (project_dir / "CLAUDE.md").write_text("""# My Project

## Project Overview
@README.md

## API Documentation
@docs/api.md

## Example Code
See the main implementation file.
""")

    # Create README.md
    (project_dir / "README.md").write_text("""# Example Project

This is an example project demonstrating the claudemd-loader library.

## Features
- Feature 1
- Feature 2
- Feature 3
""")

    # Create docs directory
    docs_dir = project_dir / "docs"
    docs_dir.mkdir()

    # Create api.md
    (docs_dir / "api.md").write_text("""# API Reference

## Endpoints

### GET /api/users
Returns a list of users.

### POST /api/users
Creates a new user.

For setup instructions, see @setup.md
""")

    # Create setup.md
    (docs_dir / "setup.md").write_text("""# Setup Instructions

1. Install dependencies
2. Configure environment
3. Run migrations
4. Start the server
""")

    return project_dir


def main() -> None:
    """Run the example."""
    print("Creating example project...")
    project_dir = create_example_project()

    try:
        print(f"\nProject created at: {project_dir}")
        print("\nProject structure:")
        for path in sorted(project_dir.rglob("*.md")):
            relative_path = path.relative_to(project_dir)
            print(f"  {relative_path}")

        print("\n" + "=" * 60)
        print("Loading CLAUDE.md with imports resolved:")
        print("=" * 60 + "\n")

        # Create context and load files
        ctx = ClaudeMdLoaderContext(project_dir)
        content = ctx.load_claudemd()

        print(content)

        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

    finally:
        # Clean up
        print(f"\nCleaning up temporary directory: {project_dir}")
        shutil.rmtree(project_dir)


if __name__ == "__main__":
    main()
