"""Example demonstrating custom project name feature."""

from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


def main() -> None:
    """Demonstrate custom project name usage."""
    print("=" * 70)
    print("Custom Project Name Example")
    print("=" * 70)

    # Example 1: Default behavior (uses directory name)
    print("\n1. Default behavior - project name from directory:")
    print("-" * 70)

    project_dir = Path(__file__).parent.parent
    ctx_default = ClaudeMdLoaderContext(project_dir)

    print(f"Directory: {project_dir.name}")
    print(f"Project name: {ctx_default.project_name}")
    print(f"Searches in: ~/.claude/projects/{ctx_default.project_name}/")

    # Example 2: Custom project name
    print("\n2. Custom project name - override directory name:")
    print("-" * 70)

    ctx_custom = ClaudeMdLoaderContext(project_dir, project_name="shared-context")

    print(f"Directory: {project_dir.name}")
    print(f"Project name: {ctx_custom.project_name}")
    print(f"Searches in: ~/.claude/projects/{ctx_custom.project_name}/")

    # Example 3: Use case - sharing context across related projects
    print("\n3. Real-world use case:")
    print("-" * 70)
    print("""
    Scenario: You have multiple related projects that share context

    Projects:
    - ~/code/myapp-frontend  (uses project_name='myapp')
    - ~/code/myapp-backend   (uses project_name='myapp')
    - ~/code/myapp-mobile    (uses project_name='myapp')

    All three can share the same context from:
    ~/.claude/projects/myapp/CLAUDE.md
    ~/.claude/projects/myapp/memory/MEMORY.md

    Code example:
    ```python
    # In frontend project
    ctx = ClaudeMdLoaderContext("~/code/myapp-frontend", project_name="myapp")

    # In backend project
    ctx = ClaudeMdLoaderContext("~/code/myapp-backend", project_name="myapp")

    # Both load the same shared context!
    ```
    """)

    print("\n" + "=" * 70)
    print("Benefits:")
    print("=" * 70)
    print("✓ Share context across related projects")
    print("✓ Team-wide conventions in one location")
    print("✓ Monorepo support with shared context")
    print("✓ Flexible project organization")


if __name__ == "__main__":
    main()
