## Quick Reference Checklist

Use this checklist when writing or reviewing your CLAUDE.md:

- Under 300 lines (ideally under 100)
- Every instruction is universally applicable to all tasks
- Includes project overview (stack, structure, purpose)
- Includes exact build/test/verify commands
- Uses progressive disclosure for detailed docs
- No code style rules (use linters and formatters instead)
- No task-specific instructions (use scoped rules or slash commands)
- No auto-generated content (hand-crafted, every line intentional)
- Pointers, not copies (reference files instead of duplicating content)
- Personal preferences in CLAUDE.local.md, not the shared file
- Scoped rules use .claude/rules/ with YAML frontmatter paths

## Key Takeaways
1. **CLAUDE.md is the highest-leverage file in your workflow.** Treat every line as precious.
2. **Less is more.** Fewer, better instructions outperform a wall of text every time.
3. **Universally applicable only.** Task-specific context belongs in scoped rules, slash commands, or reference docs.
4. **Use progressive disclosure.** Point Claude to detailed docs; don't inline everything.
5. **Don't use it as a linter.** Deterministic tools (linters, formatters, hooks) are faster, cheaper, and more reliable.
6. **Hand-craft it**. Auto-generation produces mediocre results for the highest-leverage file in your setup.
7. **Use the full hierarchy.** Root CLAUDE.md, CLAUDE.local.md, **.claude/rules/**, slash commands, and hooks each serve a specific purpose.