"""
Example showing how missing file warnings work.
"""

import shutil
import tempfile
import warnings
from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


def main() -> None:
    # Create a temporary project
    project_dir = Path(tempfile.mkdtemp(prefix="warning_example_"))

    try:
        # Create CLAUDE.md with references to existing and missing files
        (project_dir / "CLAUDE.md").write_text("""# Test Project

## Existing Content
@existing.md

## Missing Content (will trigger warning)
@missing1.md

## More Existing Content
@another.md

## Another Missing (will trigger warning)
@missing2.md
""")

        # Create only some of the referenced files
        (project_dir / "existing.md").write_text("This file exists!")
        (project_dir / "another.md").write_text("This one too!")

        print("Loading CLAUDE.md with missing files...\n")
        print("=" * 60)

        # Load with default warning behavior
        print("\n1. Default behavior (warnings printed to stderr):\n")
        ctx = ClaudeMdLoaderContext(project_dir)
        result = ctx.load_claudemd()

        print("\nResult:")
        print(result)

        # Load and capture warnings programmatically
        print("\n" + "=" * 60)
        print("\n2. Capturing warnings programmatically:\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            ctx = ClaudeMdLoaderContext(project_dir)
            result = ctx.load_claudemd()

            if w:
                print(f"Captured {len(w)} warning(s):")
                for warning in w:
                    print(f"  - {warning.category.__name__}: {warning.message}")
            else:
                print("No warnings captured")

        print("\n" + "=" * 60)
        print("\nNote: Missing files produce both:")
        print("  1. Python warnings (shown above)")
        print("  2. HTML comments in the output (<!-- File not found: ... -->)")
        print("\nThis allows both programmatic detection via warnings")
        print("and visibility in the generated content.")

    finally:
        # Clean up
        shutil.rmtree(project_dir)


if __name__ == "__main__":
    main()
