import os
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest

from claudemd_loader import ClaudeMdLoaderContext


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with test files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


def test_basic_loading(temp_project: Path) -> None:
    """Test loading a simple CLAUDE.md file."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Test Project\n\nThis is a test.")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "# Test Project" in result
    assert "This is a test." in result


def test_simple_import(temp_project: Path) -> None:
    """Test importing another file."""
    readme = temp_project / "README.md"
    readme.write_text("# README\n\nProject documentation.")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main\n\n@README.md")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "# Main" in result
    assert "# README" in result
    assert "Project documentation" in result


def test_import_without_extension(temp_project: Path) -> None:
    """Test importing a file without specifying extension."""
    readme = temp_project / "README.md"
    readme.write_text("# README Content")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("See @README for details.")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "# README Content" in result


def test_subdirectory_import(temp_project: Path) -> None:
    """Test importing from a subdirectory."""
    docs_dir = temp_project / "docs"
    docs_dir.mkdir()

    guide = docs_dir / "guide.md"
    guide.write_text("# Guide\n\nDetailed instructions.")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("Check @docs/guide.md")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "# Guide" in result
    assert "Detailed instructions" in result


def test_relative_path_resolution(temp_project: Path) -> None:
    """Test that relative imports work correctly from nested files."""
    docs_dir = temp_project / "docs"
    docs_dir.mkdir()

    helper = docs_dir / "helper.md"
    helper.write_text("Helper content")

    main_doc = docs_dir / "main.md"
    main_doc.write_text("Main doc.\n\n@helper.md")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@docs/main.md")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Main doc" in result
    assert "Helper content" in result


def test_circular_import_detection(temp_project: Path) -> None:
    """Test that circular imports are detected and handled."""
    file_a = temp_project / "a.md"
    file_a.write_text("File A\n\n@b.md")

    file_b = temp_project / "b.md"
    file_b.write_text("File B\n\n@a.md")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@a.md")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "File A" in result
    assert "File B" in result
    assert "Circular import detected" in result


def test_max_recursion_depth(temp_project: Path) -> None:
    """Test that maximum recursion depth is enforced."""
    # Create a chain of imports that exceeds max depth
    num_files = 10
    for i in range(num_files):
        file_path = temp_project / f"file{i}.md"
        if i < num_files - 1:
            file_path.write_text(f"Level {i}\n\n@file{i+1}.md")
        else:
            file_path.write_text(f"Level {i}")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@file0.md")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Level 0" in result
    assert "Max recursion depth" in result


def test_import_in_code_block_ignored(temp_project: Path) -> None:
    """Test that imports inside code blocks are not processed."""
    readme = temp_project / "README.md"
    readme.write_text("This should not be loaded")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("""# Test

```bash
# Run this command:
@README.md
```

This is normal text.""")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "```bash" in result
    assert "@README.md" in result
    assert "This should not be loaded" not in result


def test_import_in_inline_code_ignored(temp_project: Path) -> None:
    """Test that imports inside inline code are not processed."""
    readme = temp_project / "README.md"
    readme.write_text("This should not be loaded")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("Use the `@README.md` file for documentation.")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "`@README.md`" in result
    assert "This should not be loaded" not in result


def test_yaml_frontmatter_parsing(temp_project: Path) -> None:
    """Test that YAML frontmatter is parsed and removed from content."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("""---
paths:
  - "src/**/*.py"
---
# Python Rules

All Python code must follow PEP 8.""")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    # Frontmatter should be removed from output
    assert "paths:" not in result
    assert "# Python Rules" in result
    assert "PEP 8" in result


def test_file_not_found(temp_project: Path) -> None:
    """Test handling of missing import files."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("Start content\n\n@nonexistent.md\n\nEnd content")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Check that a warning is emitted
    with pytest.warns(UserWarning, match="File not found.*nonexistent"):
        result = ctx.load_claudemd()

    # Should have both content and HTML comment
    assert "Start content" in result
    assert "End content" in result
    assert "<!-- File not found" in result  # HTML comment should be present


def test_multiple_missing_files(temp_project: Path) -> None:
    """Test that multiple missing files each emit warnings."""
    existing = temp_project / "existing.md"
    existing.write_text("I exist!")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@missing1.md\n\n@existing.md\n\n@missing2.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Check that warnings are emitted for both missing files
    with pytest.warns(UserWarning, match="File not found") as warning_list:
        result = ctx.load_claudemd()

    # Should have 2 warnings
    expected_warnings = 2
    assert len(warning_list) == expected_warnings
    warning_messages = [str(w.message) for w in warning_list]
    assert any("missing1" in msg for msg in warning_messages)
    assert any("missing2" in msg for msg in warning_messages)

    # Existing file should be loaded
    assert "I exist!" in result
    # HTML comments should be present for missing files
    assert "<!-- File not found" in result
    assert result.count("<!-- File not found") == expected_warnings


def test_multiple_imports_in_one_file(temp_project: Path) -> None:
    """Test multiple imports in a single file."""
    file1 = temp_project / "file1.md"
    file1.write_text("Content 1")

    file2 = temp_project / "file2.md"
    file2.write_text("Content 2")

    file3 = temp_project / "file3.md"
    file3.write_text("Content 3")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@file1.md\n\nMiddle section\n\n@file2.md\n\nMore text\n\n@file3.md")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Content 1" in result
    assert "Content 2" in result
    assert "Content 3" in result
    assert "Middle section" in result
    assert "More text" in result


def test_json_file_import(temp_project: Path) -> None:
    """Test importing a JSON file."""
    package_json = temp_project / "package.json"
    package_json.write_text('{"name": "test", "version": "1.0.0"}')

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("Package info:\n\n@package.json")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert '"name": "test"' in result
    assert '"version": "1.0.0"' in result


def test_custom_claudemd_filename(temp_project: Path) -> None:
    """Test loading with a custom CLAUDE.md filename."""
    custom_file = temp_project / "MY_CONTEXT.md"
    custom_file.write_text("# Custom Context File\n\nThis is a custom context.")

    ctx = ClaudeMdLoaderContext(temp_project, claudemd_filename="MY_CONTEXT.md")
    result = ctx.load_claudemd()

    assert "# Custom Context File" in result
    assert "This is a custom context" in result


def test_custom_max_recursion_depth(temp_project: Path) -> None:
    """Test that custom maximum recursion depth is enforced."""
    # Create a chain of imports that exceeds custom max depth of 3
    num_files = 6
    for i in range(num_files):
        file_path = temp_project / f"file{i}.md"
        if i < num_files - 1:
            file_path.write_text(f"Level {i}\n\n@file{i+1}.md")
        else:
            file_path.write_text(f"Level {i}")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@file0.md")

    # Use custom max depth of 3 instead of default 5
    ctx = ClaudeMdLoaderContext(temp_project, max_recursion_depth=3)
    result = ctx.load_claudemd()

    assert "Level 0" in result
    assert "Max recursion depth (3) exceeded" in result
    # With depth 3, we shouldn't reach Level 4
    assert "Level 4" not in result


def test_missing_main_claudemd_file(temp_project: Path) -> None:
    """Test warning when main CLAUDE.md file doesn't exist."""
    # Don't create CLAUDE.md file
    ctx = ClaudeMdLoaderContext(temp_project)

    # Check that a warning is emitted for missing main file
    with pytest.warns(UserWarning, match="No CLAUDE.md files found"):
        result = ctx.load_claudemd()

    # Should return empty string
    assert result == ""


def test_project_dir_not_directory(tmp_path: Path) -> None:
    """Test that NotADirectoryError is raised when project_dir is not a directory."""
    # Create a file instead of a directory
    file_path = tmp_path / "not_a_directory.txt"
    file_path.write_text("This is a file, not a directory")

    # Should raise NotADirectoryError
    with pytest.raises(NotADirectoryError, match="project_dir must be a directory"):
        ClaudeMdLoaderContext(file_path)


def test_load_from_claude_projects_directory(tmp_path: Path) -> None:
    """Test loading CLAUDE.md from ~/.claude/projects/<project-name>/."""
    # Create a project directory
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # Create ~/.claude/projects/<project-name>/ directory
    claude_projects_dir = Path.home() / ".claude" / "projects" / "my_project"
    claude_projects_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create CLAUDE.md in the .claude/projects directory (not in project dir)
        claude_md = claude_projects_dir / "CLAUDE.md"
        claude_md.write_text("# Global Project Context\n\nFrom .claude/projects/")

        # Load should find it in .claude/projects/
        ctx = ClaudeMdLoaderContext(project_dir)
        result = ctx.load_claudemd()

        assert "Global Project Context" in result
        assert "From .claude/projects/" in result
    finally:
        # Clean up
        if claude_projects_dir.exists():
            shutil.rmtree(claude_projects_dir)


def test_project_dir_loads_with_claude_projects(tmp_path: Path) -> None:
    """Test that both project dir CLAUDE.md and ~/.claude/projects/ are loaded."""
    # Create a project directory
    project_dir = tmp_path / "priority_test"
    project_dir.mkdir()

    # Create CLAUDE.md in project directory
    (project_dir / "CLAUDE.md").write_text("# Local Project Context")

    # Create ~/.claude/projects/<project-name>/ directory
    claude_projects_dir = Path.home() / ".claude" / "projects" / "priority_test"
    claude_projects_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create CLAUDE.md in .claude/projects directory too
        (claude_projects_dir / "CLAUDE.md").write_text("# Global Project Context")

        # Load should include both files (global first, then local)
        ctx = ClaudeMdLoaderContext(project_dir)
        result = ctx.load_claudemd()

        assert "Local Project Context" in result
        assert "Global Project Context" in result
        # Global should come before local
        assert result.index("Global Project Context") < result.index("Local Project Context")
    finally:
        # Clean up
        if claude_projects_dir.exists():
            shutil.rmtree(claude_projects_dir)


def test_custom_project_name(tmp_path: Path) -> None:
    """Test that custom project_name is used for .claude/projects/ lookups."""
    # Create a project directory with one name
    project_dir = tmp_path / "actual_dir_name"
    project_dir.mkdir()

    # Create ~/.claude/projects/<custom-name>/ directory
    custom_name = "custom_project_name"
    claude_projects_dir = Path.home() / ".claude" / "projects" / custom_name
    claude_projects_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create CLAUDE.md in the custom-named .claude/projects directory
        claude_md = claude_projects_dir / "CLAUDE.md"
        claude_md.write_text("# Custom Named Project Context")

        # Use custom project name
        ctx = ClaudeMdLoaderContext(project_dir, project_name=custom_name)
        result = ctx.load_claudemd()

        # Should find it using the custom name
        assert "Custom Named Project Context" in result
        assert ctx.project_name == custom_name
    finally:
        # Clean up
        if claude_projects_dir.exists():
            shutil.rmtree(claude_projects_dir)


def test_default_project_name_from_directory(tmp_path: Path) -> None:
    """Test that project_name defaults to directory name when not provided."""
    # Create a project directory
    project_dir = tmp_path / "my_directory"
    project_dir.mkdir()

    # Create context without custom project_name
    ctx = ClaudeMdLoaderContext(project_dir)

    # Should use directory name as project_name
    assert ctx.project_name == "my_directory"


def test_custom_project_name_with_memory(tmp_path: Path) -> None:
    """Test that custom project_name works with memory integration."""
    # Create a project directory
    project_dir = tmp_path / "actual_dir"
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text("# Main Content")

    # Create memory in custom-named location
    custom_name = "shared_context"
    memory_dir = Path.home() / ".claude" / "projects" / custom_name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        (memory_dir / "MEMORY.md").write_text("# Custom Memory Content")

        # Use custom project name
        ctx = ClaudeMdLoaderContext(project_dir, project_name=custom_name, use_memory=True)
        result = ctx.load_claudemd()

        # Should include memory from custom-named location
        assert "Custom Memory Content" in result
        assert "Main Content" in result
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_load_user_global_claude_md(tmp_path: Path) -> None:
    """Test loading from ~/.claude/CLAUDE.md."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create user global CLAUDE.md
    user_claude_dir = Path.home() / ".claude"
    user_claude_dir.mkdir(parents=True, exist_ok=True)
    user_global_file = user_claude_dir / "CLAUDE.md"

    try:
        user_global_file.write_text("# User Global Context")

        ctx = ClaudeMdLoaderContext(project_dir)
        result = ctx.load_claudemd()

        assert "User Global Context" in result
    finally:
        # Clean up
        if user_global_file.exists():
            user_global_file.unlink()


def test_load_project_claude_directory(temp_project: Path) -> None:
    """Test loading from .claude/CLAUDE.md in project."""
    # Create .claude directory in project
    claude_dir = temp_project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "CLAUDE.md").write_text("# Project .claude Context")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Project .claude Context" in result


def test_load_claude_local_md(temp_project: Path) -> None:
    """Test loading from CLAUDE.local.md in project."""
    (temp_project / "CLAUDE.local.md").write_text("# Local Personal Context")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Local Personal Context" in result


def test_multi_file_loading_order(tmp_path: Path) -> None:
    """Test that multiple CLAUDE.md files are loaded in correct order."""
    project_dir = tmp_path / "multifile_test"
    project_dir.mkdir()

    # Create user global
    user_claude_dir = Path.home() / ".claude"
    user_claude_dir.mkdir(parents=True, exist_ok=True)
    user_global_file = user_claude_dir / "CLAUDE.md"

    # Create user project-specific
    user_project_dir = Path.home() / ".claude" / "projects" / "multifile_test"
    user_project_dir.mkdir(parents=True, exist_ok=True)

    try:
        user_global_file.write_text("# 1-Global")
        (user_project_dir / "CLAUDE.md").write_text("# 2-UserProject")
        (project_dir / "CLAUDE.md").write_text("# 3-ProjectRoot")
        (project_dir / ".claude").mkdir()
        (project_dir / ".claude" / "CLAUDE.md").write_text("# 4-ProjectClaude")
        (project_dir / "CLAUDE.local.md").write_text("# 5-Local")

        ctx = ClaudeMdLoaderContext(project_dir)
        result = ctx.load_claudemd()

        # All should be present
        assert "1-Global" in result
        assert "2-UserProject" in result
        assert "3-ProjectRoot" in result
        assert "4-ProjectClaude" in result
        assert "5-Local" in result

        # Check order (global first, local last)
        assert result.index("1-Global") < result.index("2-UserProject")
        assert result.index("2-UserProject") < result.index("3-ProjectRoot")
        assert result.index("3-ProjectRoot") < result.index("4-ProjectClaude")
        assert result.index("4-ProjectClaude") < result.index("5-Local")
    finally:
        # Clean up
        if user_global_file.exists():
            user_global_file.unlink()
        if user_project_dir.exists():
            shutil.rmtree(user_project_dir)


def test_extra_claude_files_parameter(temp_project: Path) -> None:
    """Test loading extra CLAUDE.md files via parameter."""
    (temp_project / "CLAUDE.md").write_text("# Main Context")

    # Create extra files
    extra_dir = temp_project / "extras"
    extra_dir.mkdir()
    extra1 = extra_dir / "extra1.md"
    extra2 = extra_dir / "extra2.md"
    extra1.write_text("# Extra 1")
    extra2.write_text("# Extra 2")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd(extra_claude_files=[str(extra1), str(extra2)])

    assert "Main Context" in result
    assert "Extra 1" in result
    assert "Extra 2" in result


def test_extra_claude_files_loaded_after_conventional(temp_project: Path) -> None:
    """Test that extra files are loaded after conventional files."""
    (temp_project / "CLAUDE.md").write_text("# A-Main")

    extra_file = temp_project / "extra.md"
    extra_file.write_text("# Z-Extra")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd(extra_claude_files=[str(extra_file)])

    # Extra should come after main
    assert result.index("A-Main") < result.index("Z-Extra")


def test_extra_claude_files_with_relative_paths(temp_project: Path) -> None:
    """Test that extra files can be specified with relative paths."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Create extra file
    extra_file = temp_project / "docs" / "extra.md"
    extra_file.parent.mkdir()
    extra_file.write_text("# Extra Content")

    ctx = ClaudeMdLoaderContext(temp_project)
    # Use relative path
    result = ctx.load_claudemd(extra_claude_files=["docs/extra.md"])

    assert "Main" in result
    assert "Extra Content" in result


def test_extra_claude_files_empty_list(temp_project: Path) -> None:
    """Test that passing empty extra_claude_files list works correctly."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd(extra_claude_files=[])

    assert "Main" in result


def test_caching_with_extra_files(temp_project: Path) -> None:
    """Test that caching works correctly with extra_claude_files."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    extra_file = temp_project / "extra.md"
    extra_file.write_text("# Extra")

    ctx = ClaudeMdLoaderContext(temp_project, caching=True)

    # First load
    result1 = ctx.load_claudemd(extra_claude_files=[str(extra_file)])
    assert "Main" in result1
    assert "Extra" in result1

    # Second load (should use cache)
    result2 = ctx.load_claudemd(extra_claude_files=[str(extra_file)])
    assert result1 == result2

    # Modify extra file and force mtime change for cross-platform cache invalidation
    extra_file.write_text("# Modified Extra")
    stat = extra_file.stat()
    os.utime(extra_file, (stat.st_atime, stat.st_mtime + 2))

    result3 = ctx.load_claudemd(extra_claude_files=[str(extra_file)])
    assert "Modified Extra" in result3


def test_load_rules_single_file(temp_project: Path) -> None:
    """Test loading a single rule file from .claude/rules/."""
    (temp_project / "CLAUDE.md").write_text("# Main Context")

    # Create rules directory and file
    rules_dir = temp_project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "api-rules.md").write_text("# API Rules")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Main Context" in result
    assert "API Rules" in result


def test_load_rules_multiple_files_sorted(temp_project: Path) -> None:
    """Test loading multiple rule files in sorted order."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Create multiple rule files (will be sorted alphabetically)
    rules_dir = temp_project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "z-last.md").write_text("# Last")
    (rules_dir / "a-first.md").write_text("# First")
    (rules_dir / "m-middle.md").write_text("# Middle")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    # Check all present
    assert "First" in result
    assert "Middle" in result
    assert "Last" in result

    # Check order (alphabetical)
    assert result.index("First") < result.index("Middle")
    assert result.index("Middle") < result.index("Last")


def test_load_rules_nested_directories(temp_project: Path) -> None:
    """Test loading rule files from nested subdirectories."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Create nested rules structure
    rules_dir = temp_project / ".claude" / "rules"
    api_dir = rules_dir / "api"
    db_dir = rules_dir / "database"

    api_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (rules_dir / "general.md").write_text("# General Rules")
    (api_dir / "rest.md").write_text("# REST API Rules")
    (db_dir / "schema.md").write_text("# Database Schema Rules")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "General Rules" in result
    assert "REST API Rules" in result
    assert "Database Schema Rules" in result


def test_load_rules_with_frontmatter(temp_project: Path) -> None:
    """Test that rules files respect frontmatter paths filtering."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Create rule file with frontmatter
    rules_dir = temp_project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "api-rules.md").write_text("""---
paths:
  - "src/api/**/*.py"
---
# API Rules

Only for API files.""")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Without context_files matching, rule should not be included
    result1 = ctx.load_claudemd(context_files=["src/utils/helper.py"])
    assert "API Rules" not in result1

    # With matching context_file, rule should be included
    result2 = ctx.load_claudemd(context_files=["src/api/users.py"])
    assert "API Rules" in result2


def test_load_rules_order_in_full_sequence(temp_project: Path) -> None:
    """Test that rules files are loaded in correct position in overall sequence."""
    # Create all file types
    (temp_project / "CLAUDE.md").write_text("# 1-Main")

    claude_dir = temp_project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "CLAUDE.md").write_text("# 2-Claude")

    rules_dir = claude_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "rule.md").write_text("# 3-Rules")

    (temp_project / "CLAUDE.local.md").write_text("# 4-Local")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    # Verify order: main files, then .claude/CLAUDE.md, then rules, then local
    assert result.index("1-Main") < result.index("2-Claude")
    assert result.index("2-Claude") < result.index("3-Rules")
    assert result.index("3-Rules") < result.index("4-Local")


def test_load_rules_empty_directory(temp_project: Path) -> None:
    """Test that empty .claude/rules/ directory doesn't cause issues."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Create empty rules directory
    rules_dir = temp_project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Main" in result


def test_load_rules_no_directory(temp_project: Path) -> None:
    """Test that missing .claude/rules/ directory doesn't cause issues."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Don't create .claude/rules/ at all

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    assert "Main" in result


def test_context_files_no_frontmatter(temp_project: Path) -> None:
    """Test that files without frontmatter are always included."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main Context\n\nNo frontmatter here.")

    ctx = ClaudeMdLoaderContext(temp_project)
    # Even with context_files, files without frontmatter are included
    result = ctx.load_claudemd(context_files=["some_file.py"])

    assert "# Main Context" in result
    assert "No frontmatter here" in result


def test_context_files_matching_pattern(temp_project: Path) -> None:
    """Test that files matching frontmatter paths are included."""
    api_rules = temp_project / "api_rules.md"
    api_rules.write_text("""---
paths:
  - "src/api/**/*.py"
---
# API Rules

All API endpoints must be documented.""")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@api_rules.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Should include when context file matches pattern
    result = ctx.load_claudemd(context_files=["src/api/handlers.py"])
    assert "# API Rules" in result
    assert "All API endpoints must be documented" in result


def test_context_files_not_matching_pattern(temp_project: Path) -> None:
    """Test that files not matching frontmatter paths are skipped."""
    api_rules = temp_project / "api_rules.md"
    api_rules.write_text("""---
paths:
  - "src/api/**/*.py"
---
# API Rules

All API endpoints must be documented.""")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("Start\n\n@api_rules.md\n\nEnd")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Should skip when context file doesn't match pattern
    result = ctx.load_claudemd(context_files=["src/utils/helpers.py"])
    assert "Start" in result
    assert "End" in result
    assert "# API Rules" not in result
    # No HTML comment, just silently skipped
    assert "Skipped" not in result
    assert "<!--" not in result


def test_context_files_multiple_patterns(temp_project: Path) -> None:
    """Test matching with multiple patterns in frontmatter."""
    rules = temp_project / "rules.md"
    rules.write_text("""---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---
# Python Rules

Follow PEP 8.""")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@rules.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Should match first pattern
    result1 = ctx.load_claudemd(context_files=["src/main.py"])
    assert "# Python Rules" in result1

    # Should match second pattern
    result2 = ctx.load_claudemd(context_files=["tests/test_main.py"])
    assert "# Python Rules" in result2

    # Should not match - silently skipped
    result3 = ctx.load_claudemd(context_files=["docs/guide.md"])
    assert "# Python Rules" not in result3
    assert "<!--" not in result3  # No HTML comments


def test_context_files_multiple_context_files(temp_project: Path) -> None:
    """Test with multiple context files, matching any triggers inclusion."""
    rules = temp_project / "rules.md"
    rules.write_text("""---
paths:
  - "src/**/*.py"
---
# Python Rules""")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@rules.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Multiple context files, one matches
    result = ctx.load_claudemd(context_files=["docs/README.md", "src/main.py", "package.json"])
    assert "# Python Rules" in result


def test_context_files_no_context_loads_all(temp_project: Path) -> None:
    """Test that no context_files means load everything."""
    rules = temp_project / "rules.md"
    rules.write_text("""---
paths:
  - "src/**/*.py"
---
# Python Rules""")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@rules.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # No context_files means load all
    result = ctx.load_claudemd()
    assert "# Python Rules" in result


def test_context_files_with_absolute_paths(temp_project: Path) -> None:
    """Test context files with absolute paths."""
    rules = temp_project / "rules.md"
    rules.write_text("""---
paths:
  - "src/**/*.py"
---
# Python Rules""")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("@rules.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Use absolute path for context file
    abs_path = temp_project / "src" / "main.py"
    result = ctx.load_claudemd(context_files=[abs_path])
    assert "# Python Rules" in result


def test_content_concatenation_with_newlines(temp_project: Path) -> None:
    """Test that imported files are properly concatenated with newlines."""
    # Create files without trailing newlines
    file1 = temp_project / "file1.md"
    file1.write_text("Content 1 without newline")

    file2 = temp_project / "file2.md"
    file2.write_text("Content 2 without newline")

    file3 = temp_project / "file3.md"
    file3.write_text("Content 3 with newline\n")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("Start\n@file1.md\nMiddle\n@file2.md\n@file3.md\nEnd")

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd()

    # All content should be present
    assert "Start" in result
    assert "Content 1 without newline" in result
    assert "Middle" in result
    assert "Content 2 without newline" in result
    assert "Content 3 with newline" in result
    assert "End" in result

    # Check that words don't run together
    assert "newlineMiddle" not in result
    assert "newlineContent" not in result
    assert "newlineEnd" not in result


def test_memory_enabled_by_default(temp_project: Path) -> None:
    """Test that memory is loaded by default."""
    # Create CLAUDE.md
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    # Create memory directory and MEMORY.md
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        (memory_dir / "MEMORY.md").write_text("# Memory Content")

        # Load with default settings (use_memory=True by default)
        ctx = ClaudeMdLoaderContext(temp_project)
        result = ctx.load_claudemd()

        # Should include memory content by default
        assert "Main Content" in result
        assert "Memory Content" in result
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_memory_can_be_disabled(temp_project: Path) -> None:
    """Test that memory loading can be disabled with use_memory=False."""
    # Create CLAUDE.md
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    # Create memory directory and MEMORY.md
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        (memory_dir / "MEMORY.md").write_text("# Memory Content\n\nThis came from memory.")

        # Load with use_memory=False to disable
        ctx = ClaudeMdLoaderContext(temp_project, use_memory=False)
        result = ctx.load_claudemd()

        # Should not include memory content when disabled
        assert "Main Content" in result
        assert "Memory Content" not in result
        assert "This came from memory" not in result
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_memory_loads_when_explicitly_enabled(temp_project: Path) -> None:
    """Test loading MEMORY.md when use_memory is explicitly set to True."""
    # Create CLAUDE.md
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    # Create memory directory and MEMORY.md
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        (memory_dir / "MEMORY.md").write_text("# Memory Content\n\nThis came from memory.")

        # Load with use_memory=True (explicit)
        ctx = ClaudeMdLoaderContext(temp_project, use_memory=True)
        result = ctx.load_claudemd()

        # Should include both memory and main content
        assert "Memory Content" in result
        assert "This came from memory" in result
        assert "Main Content" in result

        # Memory should come before main content
        assert result.index("Memory Content") < result.index("Main Content")
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_memory_first_200_lines_only(temp_project: Path) -> None:
    """Test that only first 200 lines of MEMORY.md are loaded."""
    # Create CLAUDE.md
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    # Create memory directory and MEMORY.md with 250 lines
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create a file with 250 lines
        memory_lines = ["# Memory Content"]
        for i in range(1, 250):
            memory_lines.append(f"Line {i}")

        (memory_dir / "MEMORY.md").write_text("\n".join(memory_lines))

        # Load with use_memory flag
        ctx = ClaudeMdLoaderContext(temp_project, use_memory=True)
        result = ctx.load_claudemd()

        # Should include lines up to 200
        assert "Line 1" in result
        assert "Line 100" in result
        assert "Line 199" in result

        # Should NOT include lines after 200 (we loaded lines 0-199, which is 200 lines)
        # Line 200 is at index 200, which should not be loaded
        result_lines = result.split("\n")
        assert "Line 200" not in result_lines
        assert "Line 249" not in result_lines
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_memory_missing_file(temp_project: Path) -> None:
    """Test that missing MEMORY.md is handled gracefully."""
    # Create CLAUDE.md but no MEMORY.md
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    # Load with use_memory flag (but no memory file exists)
    ctx = ClaudeMdLoaderContext(temp_project, use_memory=True)
    result = ctx.load_claudemd()

    # Should still work, just without memory content
    assert "Main Content" in result


def test_memory_with_custom_claudemd_filename(temp_project: Path) -> None:
    """Test that memory works with custom CLAUDE.md filename."""
    # Create custom filename
    (temp_project / "CONTEXT.md").write_text("# Custom Content")

    # Create memory directory and MEMORY.md
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        (memory_dir / "MEMORY.md").write_text("# Memory Content")

        # Load with custom filename and use_memory flag
        ctx = ClaudeMdLoaderContext(temp_project, claudemd_filename="CONTEXT.md", use_memory=True)
        result = ctx.load_claudemd()

        # Should include both memory and custom content
        assert "Memory Content" in result
        assert "Custom Content" in result
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_caching_enabled_by_default(temp_project: Path) -> None:
    """Test that caching is enabled by default and automatically invalidates on file changes."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main Content")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load
    result1 = ctx.load_claudemd()
    assert "Main Content" in result1

    # Second load without file changes should return cached result
    result2 = ctx.load_claudemd()
    assert result2 == result1  # Exact same content from cache

    # Modify the file and force mtime change for cross-platform cache invalidation
    claude_md.write_text("# Modified Content")
    stat = claude_md.stat()
    os.utime(claude_md, (stat.st_atime, stat.st_mtime + 2))

    # Third load should automatically detect file change and reload
    result3 = ctx.load_claudemd()
    assert "Modified Content" in result3
    assert "Main Content" not in result3


def test_caching_with_context_files(temp_project: Path) -> None:
    """Test that caching works with context_files."""
    # Create files
    (temp_project / "CLAUDE.md").write_text(
        "---\ncontext_files:\n  - src/**/*.py\n---\n\n# Main Content"
    )
    (temp_project / "README.md").write_text("# README")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load with specific context files
    result1 = ctx.load_claudemd(context_files=["src/main.py", "src/utils.py"])

    # Second load with same context files (should be cached)
    result2 = ctx.load_claudemd(context_files=["src/main.py", "src/utils.py"])

    # Should return the same result
    assert result1 == result2


def test_caching_order_independent(temp_project: Path) -> None:
    """Test that cache key is order-independent."""
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Load with files in one order
    result1 = ctx.load_claudemd(context_files=["file1.py", "file2.py", "file3.py"])

    # Load with files in different order
    result2 = ctx.load_claudemd(context_files=["file3.py", "file1.py", "file2.py"])

    # Should return the same cached result
    assert result1 == result2


def test_caching_different_context_files(temp_project: Path) -> None:
    """Test that different context_files result in different cache entries."""
    # Create CLAUDE.md with frontmatter
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text(
        "---\ncontext_files:\n  - src/**/*.py\n---\n\n# Main Content"
    )

    ctx = ClaudeMdLoaderContext(temp_project)

    # Load with one set of context files (to populate cache)
    ctx.load_claudemd(context_files=["src/main.py"])

    # Modify the file
    claude_md.write_text(
        "---\ncontext_files:\n  - src/**/*.py\n---\n\n# Modified"
    )

    # Load with different context files (different cache key, should reload)
    result2 = ctx.load_claudemd(context_files=["src/utils.py"])

    # Should load the modified content (different cache key)
    assert "Modified" in result2


def test_caching_can_be_disabled(temp_project: Path) -> None:
    """Test that caching can be disabled."""
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    ctx = ClaudeMdLoaderContext(temp_project, caching=False)

    # First load
    result1 = ctx.load_claudemd()
    assert "Main Content" in result1

    # Modify the file
    (temp_project / "CLAUDE.md").write_text("# Modified Content")

    # Second load should return the modified content (caching disabled)
    result2 = ctx.load_claudemd()
    assert "Modified Content" in result2
    assert "Main Content" not in result2


def test_invalidate_cache(temp_project: Path) -> None:
    """Test that invalidate_cache() clears the cache."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main Content")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load (cached)
    result1 = ctx.load_claudemd()
    assert "Main Content" in result1

    # Verify cache is being used (load again)
    result2 = ctx.load_claudemd()
    assert result2 == result1

    # Manually invalidate cache
    ctx.invalidate_cache()

    # Even without file changes, should reload after manual invalidation
    # (can verify by checking internal cache state)
    assert len(ctx._cache) == 0

    # Load again - will repopulate cache
    result3 = ctx.load_claudemd()
    assert "Main Content" in result3


def test_cache_persists_across_multiple_loads(temp_project: Path) -> None:
    """Test that cache persists across multiple loads."""
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Multiple loads with same context_files
    result1 = ctx.load_claudemd(context_files=["src/main.py"])
    result2 = ctx.load_claudemd(context_files=["src/main.py"])
    result3 = ctx.load_claudemd(context_files=["src/main.py"])

    # All should return the same cached result
    assert result1 == result2 == result3


def test_cache_with_none_context_files(temp_project: Path) -> None:
    """Test that cache works when context_files is None."""
    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main Content")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load with None
    result1 = ctx.load_claudemd(context_files=None)
    assert "Main Content" in result1

    # Second load with None (should be cached, file hasn't changed)
    result2 = ctx.load_claudemd(context_files=None)
    assert result2 == result1

    # Also test with no argument (defaults to None)
    result3 = ctx.load_claudemd()
    assert result3 == result2


def test_cache_invalidates_on_imported_file_change(temp_project: Path) -> None:
    """Test that cache invalidates when an imported file changes."""
    # Create files
    readme = temp_project / "README.md"
    readme.write_text("# Original README")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main\\n\\n@README.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load
    result1 = ctx.load_claudemd()
    assert "Original README" in result1

    # Second load (should be cached)
    result2 = ctx.load_claudemd()
    assert result2 == result1

    # Modify the imported file and force mtime change for cross-platform cache invalidation
    readme.write_text("# Modified README")
    stat = readme.stat()
    os.utime(readme, (stat.st_atime, stat.st_mtime + 2))

    # Third load should detect the change and reload
    result3 = ctx.load_claudemd()
    assert "Modified README" in result3
    assert "Original README" not in result3


def test_cache_invalidates_on_memory_file_change(temp_project: Path) -> None:
    """Test that cache invalidates when MEMORY.md changes."""
    # Create CLAUDE.md
    (temp_project / "CLAUDE.md").write_text("# Main Content")

    # Create memory directory and file
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        memory_file = memory_dir / "MEMORY.md"
        memory_file.write_text("# Original Memory")

        ctx = ClaudeMdLoaderContext(temp_project, use_memory=True)

        # First load
        result1 = ctx.load_claudemd()
        assert "Original Memory" in result1
        assert "Main Content" in result1

        # Second load (should be cached)
        result2 = ctx.load_claudemd()
        assert result2 == result1

        # Modify the memory file and force mtime change for cross-platform cache invalidation
        memory_file.write_text("# Modified Memory")
        stat = memory_file.stat()
        os.utime(memory_file, (stat.st_atime, stat.st_mtime + 2))

        # Third load should detect the change and reload
        result3 = ctx.load_claudemd()
        assert "Modified Memory" in result3
        assert "Original Memory" not in result3
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_cache_invalidates_on_file_deletion(temp_project: Path) -> None:
    """Test that cache invalidates when a tracked file is deleted."""
    # Create files
    readme = temp_project / "README.md"
    readme.write_text("# README")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main\\n\\n@README.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load
    result1 = ctx.load_claudemd()
    assert "README" in result1

    # Delete the imported file
    readme.unlink()

    # Modify CLAUDE.md to remove the import that now fails
    claude_md.write_text("# Main Only")

    # Load again - should detect file changes and reload
    result2 = ctx.load_claudemd()
    assert "Main Only" in result2


def test_cache_tracks_multiple_imported_files(temp_project: Path) -> None:
    """Test that cache tracks modification times for all imported files."""
    # Create multiple files
    (temp_project / "file1.md").write_text("# File 1")
    (temp_project / "file2.md").write_text("# File 2")
    (temp_project / "file3.md").write_text("# File 3")

    claude_md = temp_project / "CLAUDE.md"
    claude_md.write_text("# Main\\n\\n@file1.md\\n\\n@file2.md\\n\\n@file3.md")

    ctx = ClaudeMdLoaderContext(temp_project)

    # First load
    result1 = ctx.load_claudemd()
    assert "File 1" in result1
    assert "File 2" in result1
    assert "File 3" in result1

    # Second load (cached)
    result2 = ctx.load_claudemd()
    assert result2 == result1

    # Modify just the middle file
    (temp_project / "file2.md").write_text("# File 2 Modified")

    # Third load should detect the change
    result3 = ctx.load_claudemd()
    assert "File 2 Modified" in result3
    assert "File 1" in result3  # Other files unchanged
    assert "File 3" in result3


def test_load_claudemd_chunks_basic(temp_project: Path) -> None:
    """Test basic chunking functionality."""
    (temp_project / "CLAUDE.md").write_text("A" * 500)  # 500 characters

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=200, chunk_overlap=0))

    # _load_file adds a newline, so 500 chars becomes 501
    # Should produce 3 chunks: 200, 200, 101
    assert len(chunks) == 3
    assert len(chunks[0][1]) == 200  # First chunk
    assert len(chunks[1][1]) == 200  # Second chunk
    assert len(chunks[2][1]) == 101  # Last chunk (includes trailing newline)

    # All chunks from same file
    assert all(temp_project.name in chunk[0] for chunk in chunks)


def test_load_claudemd_chunks_with_overlap(temp_project: Path) -> None:
    """Test chunking with overlap."""
    (temp_project / "CLAUDE.md").write_text("ABCDEFGHIJ" * 50)  # 500 chars

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=100, chunk_overlap=20))

    # Verify overlap exists
    assert len(chunks) > 1
    # Check that consecutive chunks overlap
    for i in range(len(chunks) - 1):
        chunk1_text = chunks[i][1]
        chunk2_text = chunks[i + 1][1]
        # Overlap should be at end of chunk1 and start of chunk2
        overlap_length = min(20, len(chunk1_text))
        assert chunk1_text[-overlap_length:] == chunk2_text[:overlap_length]


def test_load_claudemd_chunks_line_numbers(temp_project: Path) -> None:
    """Test that line numbers are correctly tracked."""
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    (temp_project / "CLAUDE.md").write_text(content)

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=15, chunk_overlap=0))

    # Verify all chunks have valid line numbers
    for _file_path, chunk_text, start_line, end_line in chunks:
        assert start_line >= 1
        assert end_line >= start_line
        # Count newlines in chunk
        newlines_in_chunk = chunk_text.count("\n")
        assert end_line == start_line + newlines_in_chunk


def test_load_claudemd_chunks_single_line(temp_project: Path) -> None:
    """Test chunking with content on single line."""
    (temp_project / "CLAUDE.md").write_text("A" * 300)

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=100, chunk_overlap=0))

    # First chunks should be on line 1, last chunk may include trailing newline (line 2)
    for i, (_file_path, _chunk_text, start_line, end_line) in enumerate(chunks):
        assert start_line == 1 if i == 0 else start_line >= 1
        # Last chunk will include the trailing newline added by _load_file
        if i == len(chunks) - 1:
            assert end_line in (1, 2)  # May have trailing newline
        else:
            assert end_line >= start_line


def test_load_claudemd_chunks_multiline(temp_project: Path) -> None:
    """Test chunking with multi-line content."""
    lines = [f"Line {i}\n" for i in range(1, 11)]
    content = "".join(lines)  # 10 lines
    (temp_project / "CLAUDE.md").write_text(content)

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=50, chunk_overlap=0))

    # Verify chunks span multiple lines
    assert len(chunks) > 1
    # At least one chunk should span multiple lines
    assert any(chunk[3] > chunk[2] for chunk in chunks)


def test_load_claudemd_chunks_multiple_files(temp_project: Path) -> None:
    """Test that chunks from different files have different paths."""
    (temp_project / "CLAUDE.md").write_text("Main content here")

    rules_dir = temp_project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "rules.md").write_text("Rules content here")

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=50, chunk_overlap=0))

    # Should have chunks from both files
    file_paths = {chunk[0] for chunk in chunks}
    assert len(file_paths) >= 2

    # Verify different files are represented
    assert any("CLAUDE.md" in path for path in file_paths)
    assert any("rules.md" in path for path in file_paths)


def test_load_claudemd_chunks_with_context_files(temp_project: Path) -> None:
    """Test chunking respects context_files filtering."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    rules_dir = temp_project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "api-rules.md").write_text("""---
paths:
  - "src/api/**/*.py"
---
# API Rules""")

    ctx = ClaudeMdLoaderContext(temp_project)

    # Without matching context_files
    chunks1 = list(ctx.load_claudemd_chunks(
        context_files=["src/utils/helper.py"],
        chunk_size=100,
    ))
    # Should only have main file chunks
    assert all("api-rules.md" not in chunk[0] for chunk in chunks1)

    # With matching context_files
    chunks2 = list(ctx.load_claudemd_chunks(
        context_files=["src/api/users.py"],
        chunk_size=100,
    ))
    # Should include API rules chunks
    assert any("api-rules.md" in chunk[0] for chunk in chunks2)


def test_load_claudemd_chunks_with_extra_files(temp_project: Path) -> None:
    """Test chunking with extra_claude_files parameter."""
    (temp_project / "CLAUDE.md").write_text("Main")

    extra_file = temp_project / "extra.md"
    extra_file.write_text("Extra content")

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(
        extra_claude_files=[str(extra_file)],
        chunk_size=50,
    ))

    # Should have chunks from both files
    file_paths = {chunk[0] for chunk in chunks}
    assert any("CLAUDE.md" in path for path in file_paths)
    assert any("extra.md" in path for path in file_paths)


def test_load_claudemd_chunks_with_memory(temp_project: Path) -> None:
    """Test chunking includes memory when enabled."""
    (temp_project / "CLAUDE.md").write_text("# Main")

    # Create memory file
    memory_dir = Path.home() / ".claude" / "projects" / temp_project.name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    try:
        (memory_dir / "MEMORY.md").write_text("# Memory Content")

        ctx = ClaudeMdLoaderContext(temp_project, use_memory=True)
        chunks = list(ctx.load_claudemd_chunks(chunk_size=50))

        # Should have chunks from memory
        file_paths = {chunk[0] for chunk in chunks}
        assert any("MEMORY.md" in path for path in file_paths)
    finally:
        # Clean up
        if memory_dir.exists():
            shutil.rmtree(memory_dir.parent)


def test_load_claudemd_chunks_empty_file(temp_project: Path) -> None:
    """Test chunking with empty file."""
    (temp_project / "CLAUDE.md").write_text("")

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=100))

    # Empty file produces no chunks
    assert len(chunks) == 0


def test_load_claudemd_chunks_small_content(temp_project: Path) -> None:
    """Test chunking when content is smaller than chunk size."""
    (temp_project / "CLAUDE.md").write_text("Small")

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=100))

    # Should have exactly one chunk
    assert len(chunks) == 1
    # _load_file adds trailing newline
    assert chunks[0][1] == "Small\n"


def test_load_claudemd_chunks_generator(temp_project: Path) -> None:
    """Test that result is a generator (not evaluated immediately)."""
    (temp_project / "CLAUDE.md").write_text("A" * 1000)

    ctx = ClaudeMdLoaderContext(temp_project)
    result = ctx.load_claudemd_chunks(chunk_size=100)

    # Should be a generator
    assert isinstance(result, Generator)

    # Consume one item
    first_chunk = next(result)
    assert len(first_chunk) == 4  # (path, text, start_line, end_line)


def test_load_claudemd_chunks_tuple_structure(temp_project: Path) -> None:
    """Test that each chunk has correct tuple structure."""
    (temp_project / "CLAUDE.md").write_text("Test content\nLine 2\n")

    ctx = ClaudeMdLoaderContext(temp_project)
    chunks = list(ctx.load_claudemd_chunks(chunk_size=50))

    for chunk in chunks:
        assert len(chunk) == 4, "Chunk should be 4-tuple"
        file_path, text, start_line, end_line = chunk

        assert isinstance(file_path, str)
        assert isinstance(text, str)
        assert isinstance(start_line, int)
        assert isinstance(end_line, int)
        assert start_line >= 1
        assert end_line >= start_line


