"""
Example demonstrating .claude/rules/ directory usage.

This example shows how to organize scoped rules in the .claude/rules/ directory.
Rules are loaded recursively and can use frontmatter for conditional loading.
"""

from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


# Typical .claude/rules/ directory structure:
#
# .claude/
#   rules/
#     api/
#       rest.md         # REST API guidelines
#       graphql.md      # GraphQL guidelines
#     database/
#       schema.md       # Database schema rules
#       migrations.md   # Migration guidelines
#     frontend/
#       react.md        # React-specific rules
#       css.md          # CSS/styling rules
#     general.md        # General coding standards
#
# All .md files are loaded recursively in alphabetical order.

print("Rules Example")
print("=" * 50)
print()

# Example 1: Basic rules loading
print("Example 1: All rules loaded")
print("-" * 50)

project_dir = Path(__file__).parent.parent.resolve()
ctx = ClaudeMdLoaderContext(project_dir)

# All .md files in .claude/rules/ are loaded automatically
content = ctx.load_claudemd()
print(f"Loaded {len(content)} characters including rules files")
print()

# Example 2: Conditional rules with frontmatter
print("Example 2: Conditional loading with frontmatter")
print("-" * 50)
print("""
You can use frontmatter in rules files to conditionally load them:

# .claude/rules/api/rest.md
---
paths:
  - "src/api/**/*.py"
  - "tests/api/**/*.py"
---
# REST API Guidelines

- Use proper HTTP status codes
- Implement rate limiting
- Document endpoints with OpenAPI

When you call load_claudemd(context_files=["src/api/users.py"]),
this rule file is included.

When you call load_claudemd(context_files=["src/utils/helper.py"]),
this rule file is excluded.
""")

# Example 3: Organization patterns
print("Example 3: Organizing rules by domain")
print("-" * 50)
print("""
Common organization patterns:

By Technology Layer:
  .claude/rules/
    frontend/
    backend/
    database/
    infrastructure/

By Feature Domain:
  .claude/rules/
    authentication/
    payments/
    notifications/
    analytics/

By Code Type:
  .claude/rules/
    api/
    services/
    models/
    tests/

Mix and match based on your project needs!
Files are loaded in alphabetical order, so you can use prefixes
like `01-general.md`, `02-specific.md` to control order.
""")
