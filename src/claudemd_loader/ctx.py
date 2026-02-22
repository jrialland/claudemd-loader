import re
import warnings
from collections.abc import Generator
from pathlib import Path

import yaml


# Constants for frontmatter parsing
_FRONTMATTER_PARTS = 2  # Expected parts when splitting frontmatter


class ClaudeMdLoaderContext:
    """Context class for loading claudemd files from a project directory."""

    def __init__(  # noqa: PLR0913
        self,
        project_dir: str | Path,
        claudemd_filename: str | None = None,
        max_recursion_depth: int = 5,
        use_memory: bool = True,
        caching: bool = True,
        project_name: str | None = None,
    ) -> None:
        """
        Initialize the context with the project directory.

        Args:
            project_dir: Path to the project directory containing CLAUDE.md.
            claudemd_filename: Optional filename for the main file (default: "CLAUDE.md").
            max_recursion_depth: Maximum depth for imports (default: 5).
            use_memory: Whether to load MEMORY.md from ~/.claude/projects/<project>/memory/
                (default: True). When enabled, loads first 200 lines.
            caching: Whether to cache loaded content based on context_files (default: True).
            project_name: Optional custom project name for ~/.claude/projects/<name>/ lookups
                (default: None). When None, uses the directory name.

        Raises:
            NotADirectoryError: If project_dir is not a directory.
        """
        self.project_dir = Path(project_dir).resolve()
        if not self.project_dir.is_dir():
            msg = f"project_dir must be a directory, got: {self.project_dir}"
            raise NotADirectoryError(msg)
        self.project_name = project_name if project_name is not None else self.project_dir.name
        self.claudemd_filename = claudemd_filename or "CLAUDE.md"
        self.use_memory = use_memory
        self.caching = caching
        self._path_stack: list[Path] = []
        self._loaded_files: set[Path] = set()
        self.max_recursion_depth = max_recursion_depth
        self._context_files: list[str] = []  # Store normalized context file paths
        # Cache stores: cache_key -> (content, {file_path: mtime})
        # cache_key is (context_files_tuple, extra_files_tuple)
        self._cache: dict[
            tuple[tuple[str, ...], tuple[str, ...]],
            tuple[str, dict[Path, float]],
        ] = {}
        self._files_read: dict[Path, float] = {}  # Track files read during current load

    def load_claudemd(
        self,
        context_files: list[str | Path] | None = None,
        extra_claude_files: list[str | Path] | None = None,
    ) -> str:
        """
        Load relevant claudemd files and return the combined content as a string.

        Args:
            context_files: Optional list of source files for the conversation.
                These filenames determine which files to load based on yaml
                frontmatter. If None, all files will be loaded.
            extra_claude_files: Optional list of additional CLAUDE.md files to load
                explicitly (default: None). These are loaded after conventional files.

        Returns:
            A string containing the combined content of the loaded claudemd files.
        """
        # Normalize context files to Unix-style paths relative to project dir
        normalized_files = self._normalize_context_files(context_files)

        # Normalize extra apply files
        normalized_extra = []
        if extra_claude_files:
            for ef in extra_claude_files:
                normalized_extra.append(str(Path(ef).resolve()))

        # Create cache key from sorted context files and extra files
        cache_key = (tuple(sorted(normalized_files)), tuple(sorted(normalized_extra)))

        # Check cache if caching is enabled
        if self.caching and cache_key in self._cache:
            cached_content, cached_mtimes = self._cache[cache_key]
            # Verify all cached files still have the same modification time
            if self._cache_is_valid(cached_mtimes):
                return cached_content
            # Cache is stale, remove it
            del self._cache[cache_key]

        # Reset state for new loading session
        self._path_stack = []
        self._loaded_files = set()
        self._context_files = normalized_files
        self._files_read = {}  # Track files read during this load

        # Collect content from all existing files
        contents = []

        for _, content in self._iter_claudemd_files(extra_claude_files):
            contents.append(content)

        # If no files found, emit warning
        if not contents:
            warnings.warn(
                "No CLAUDE.md files found in conventional locations or extra files",
                UserWarning,
                stacklevel=2,
            )

        # Combine all content
        result = "\n\n".join(contents)

        # If use_memory is enabled, prepend MEMORY.md content
        if self.use_memory and result:
            memory_content = self._load_memory()
            if memory_content:
                result = memory_content + "\n\n" + result

        # Cache the result with file modification times if caching is enabled
        if self.caching:
            self._cache[cache_key] = (result, self._files_read.copy())

        return result

    def load_claudemd_chunks(
        self,
        context_files: list[str | Path] | None = None,
        extra_claude_files: list[str | Path] | None = None,
        chunk_size: int = 200,
        chunk_overlap: int = 0,
    ) -> Generator[tuple[str, str, int, int], None, None]:
        """
        Load claudemd files and yield chunks suitable for vector databases (RAG).

        This method loads the same files as load_claudemd but returns individual chunks
        instead of concatenated content. Each chunk includes source file information
        and line numbers for reference.

        Args:
            context_files: Optional list of source files for the conversation.
                These filenames determine which files to load based on yaml
                frontmatter. If None, all files will be loaded.
            extra_claude_files: Optional list of additional CLAUDE.md files to load
                explicitly (default: None). These are loaded after conventional files.
            chunk_size: Maximum size of each text chunk in characters (default: 200).
            chunk_overlap: Number of characters to overlap between chunks (default: 0).

        Yields:
            Tuples of (file_path, chunk_text, start_line, end_line) where:
            - file_path: String path to the source file
            - chunk_text: The text content of the chunk
            - start_line: Line number where chunk starts (1-based)
            - end_line: Line number where chunk ends (1-based)

        Example:
            >>> ctx = ClaudeMdLoaderContext("/path/to/project")
            >>> for path, chunk, start, end in ctx.load_claudemd_chunks(chunk_size=500):
            ...     print(f"{path}:{start}-{end} = {len(chunk)} chars")
        """
        # Normalize context files (same as load_claudemd)
        self._context_files = self._normalize_context_files(context_files)

        # Reset state for new loading session
        self._path_stack = []
        self._loaded_files = set()
        # self._context_files is set above
        self._files_read = {}

        # Prepend memory if enabled
        if self.use_memory:
            memory_content = self._load_memory()
            if memory_content:
                memory_path = (
                    Path.home()
                    / ".claude"
                    / "projects"
                    / self.project_name
                    / "memory"
                    / "MEMORY.md"
                )
                yield from self._chunk_content(
                    str(memory_path),
                    memory_content,
                    chunk_size,
                    chunk_overlap,
                )

        # Load and chunk conventional files
        for file_path, content in self._iter_claudemd_files(extra_claude_files):
            yield from self._chunk_content(
                str(file_path),
                content,
                chunk_size,
                chunk_overlap,
            )

    def _normalize_context_files(self, context_files: list[str | Path] | None) -> list[str]:
        """
        Normalize context files to Unix-style paths relative to project dir.

        Args:
            context_files: List of file paths or None

        Returns:
            List of normalized file path strings
        """
        if not context_files:
            return []

        normalized_files = []
        for cf in context_files:
            cf_path = Path(cf)
            # Convert to Unix-style path separator for pattern matching
            if cf_path.is_absolute():
                try:
                    rel_path = cf_path.relative_to(self.project_dir)
                    normalized_files.append(str(rel_path).replace("\\", "/"))
                except ValueError:
                    # File is outside project dir, use as-is
                    normalized_files.append(str(cf_path).replace("\\", "/"))
            else:
                normalized_files.append(str(cf_path).replace("\\", "/"))
        return normalized_files

    def _iter_claudemd_files(  # noqa: PLR0912
        self,
        extra_claude_files: list[str | Path] | None = None
    ) -> Generator[tuple[Path, str], None, None]:
        """
        Iterate over all CLAUDE.md files in conventional locations and extra files.

        Args:
            extra_claude_files: Optional list of additional CLAUDE.md files to load

        Yields:
             Tuples of (file_path, content)
        """
        # Define conventional CLAUDE.md file locations in priority order:
        # 1. User global (~/.claude/CLAUDE.md)
        # 2. Project-specific user directory (~/.claude/projects/<project>/CLAUDE.md)
        # 3. Project root (./CLAUDE.md)
        # 4. Project .claude directory (./.claude/CLAUDE.md)
        # 5. Project .claude rules (./.claude/rules/**/*.md)
        # 6. Local personal file (./CLAUDE.local.md)
        conventional_paths = [
            Path.home() / ".claude" / self.claudemd_filename,
            Path.home() / ".claude" / "projects" / self.project_name / self.claudemd_filename,
            self.project_dir / self.claudemd_filename,
            self.project_dir / ".claude" / self.claudemd_filename,
        ]

        # Load conventional files
        for file_path in conventional_paths:
            if file_path.exists():
                content = self._load_file(file_path, depth=0)
                if content:
                    yield file_path, content

        # Load all .md files from .claude/rules/ recursively
        rules_dir = self.project_dir / ".claude" / "rules"
        if rules_dir.exists() and rules_dir.is_dir():
            # Find all .md files recursively and sort for consistent ordering
            rule_files = sorted(rules_dir.rglob("*.md"))
            for rule_file in rule_files:
                content = self._load_file(rule_file, depth=0)
                if content:
                    yield rule_file, content

        # Load local personal file
        local_file = self.project_dir / "CLAUDE.local.md"
        if local_file.exists():
            content = self._load_file(local_file, depth=0)
            if content:
                yield local_file, content

        # Load extra files if specified
        if extra_claude_files:
            for extra_file in extra_claude_files:
                extra_path = Path(extra_file)
                if not extra_path.is_absolute():
                    extra_path = self.project_dir / extra_path
                extra_path = extra_path.resolve()

                if extra_path.exists():
                    content = self._load_file(extra_path, depth=0)
                    if content:
                        yield extra_path, content

    def _chunk_content(
        self,
        file_path: str,
        content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> Generator[tuple[str, str, int, int], None, None]:
        """
        Split content into overlapping chunks and yield with source information.

        Args:
            file_path: Path to the source file
            content: The text content to chunk
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks

        Yields:
            Tuples of (file_path, chunk_text, start_line, end_line)
        """
        if not content:
            return

        # Split content into lines for line number tracking
        content.split("\n")

        # Track current position
        current_pos = 0

        while current_pos < len(content):
            # Extract chunk
            chunk_end = min(current_pos + chunk_size, len(content))
            chunk_text = content[current_pos:chunk_end]

            # Calculate line numbers for this chunk
            # Count newlines before current position to get start line
            text_before = content[:current_pos]
            start_line = text_before.count("\n") + 1

            # Count newlines in chunk to get end line
            end_line = start_line + chunk_text.count("\n")

            yield (file_path, chunk_text, start_line, end_line)

            # Move to next chunk with overlap
            step = chunk_size - chunk_overlap
            if step <= 0:
                # Prevent infinite loop if overlap >= chunk_size
                step = 1

            current_pos += step

            # Stop if we're at the end
            if current_pos >= len(content):
                break

    def invalidate_cache(self) -> None:
        """
        Clear all cached content.

        Note: With modification time-based caching, manual invalidation is rarely needed
        as the cache automatically invalidates when files change.
        """
        self._cache.clear()

    def _cache_is_valid(self, cached_mtimes: dict[Path, float]) -> bool:
        """
        Check if cached content is still valid by comparing file modification times.

        Args:
            cached_mtimes: Dictionary of file paths to their cached modification times.

        Returns:
            True if all files still have the same modification time, False otherwise.
        """
        for file_path, cached_mtime in cached_mtimes.items():
            if not file_path.exists():
                # File was deleted, cache is invalid
                return False
            try:
                current_mtime = file_path.stat().st_mtime
                if current_mtime != cached_mtime:
                    # File was modified, cache is invalid
                    return False
            except OSError:
                # Error accessing file, invalidate cache
                return False
        return True

    def _load_memory(self) -> str:
        """
        Load MEMORY.md from ~/.claude/projects/<project-name>/memory/.

        Returns:
            First 200 lines of MEMORY.md if it exists, empty string otherwise.
        """
        memory_path = (
            Path.home() / ".claude" / "projects" / self.project_name / "memory" / "MEMORY.md"
        )

        if not memory_path.exists():
            return ""

        try:
            # Track the memory file's modification time
            self._files_read[memory_path] = memory_path.stat().st_mtime

            with memory_path.open(encoding="utf-8") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 200:  # noqa: PLR2004
                        break
                    lines.append(line.rstrip("\n\r"))
                return "\n".join(lines)
        except Exception:
            # Silently ignore errors reading memory file
            return ""

    def _load_file(self, file_path: Path, depth: int) -> str:
        """
        Load a single file and process its imports.

        Args:
            file_path: Path to the file to load
            depth: Current recursion depth

        Returns:
            Processed content of the file
        """
        # Check recursion depth
        if depth > self.max_recursion_depth:
            return (
                f"<!-- Max recursion depth ({self.max_recursion_depth}) "
                f"exceeded for {file_path} -->"
            )

        # Resolve the file path
        resolved_path = file_path.resolve()

        # Check for infinite loops
        if resolved_path in self._loaded_files:
            return f"<!-- Circular import detected: {file_path} -->"

        # Check if file exists
        if not resolved_path.exists():
            warnings.warn(f"File not found: {file_path}", UserWarning, stacklevel=2)
            return f"<!-- File not found: {file_path} -->"

        # Mark file as loaded
        self._loaded_files.add(resolved_path)

        # Push current path onto stack
        self._path_stack.append(resolved_path.parent)

        try:
            # Track the file's modification time for cache invalidation
            self._files_read[resolved_path] = resolved_path.stat().st_mtime

            # Read file content
            content = resolved_path.read_text(encoding="utf-8")

            # Parse YAML frontmatter if present
            content_without_frontmatter, frontmatter = self._parse_frontmatter(content)

            # Check if this file should be included based on frontmatter paths
            if not self._should_include_file(frontmatter):
                return ""

            # Process imports in the content
            processed_content = self._process_imports(content_without_frontmatter, depth)

            # Ensure content ends with newline for proper concatenation
            if processed_content and not processed_content.endswith("\n"):
                processed_content += "\n"

            return processed_content

        finally:
            # Pop path from stack
            self._path_stack.pop()
            # Remove from loaded files to allow loading in different branches
            self._loaded_files.discard(resolved_path)

    def _parse_frontmatter(self, content: str) -> tuple[str, dict | None]:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (content without frontmatter, frontmatter dict or None)
        """
        # Check for YAML frontmatter
        if content.startswith("---\n"):
            parts = content.split("\n---\n", _FRONTMATTER_PARTS)
            if len(parts) >= _FRONTMATTER_PARTS:
                try:
                    frontmatter = yaml.safe_load(parts[0][4:])  # Skip first '---\n'
                    remaining_content = (
                        parts[1]
                        if len(parts) == _FRONTMATTER_PARTS
                        else "\n---\n".join(parts[1:])
                    )
                    return remaining_content, frontmatter
                except yaml.YAMLError:
                    # If YAML parsing fails, treat as regular content
                    pass

        return content, None

    def _should_include_file(self, frontmatter: dict | None) -> bool:
        """
        Determine if a file should be included based on frontmatter paths and context_files.

        Args:
            frontmatter: Parsed YAML frontmatter (or None if no frontmatter)

        Returns:
            True if the file should be included, False otherwise
        """
        # If no context_files specified, include everything
        if not self._context_files:
            return True

        # If no frontmatter or no paths in frontmatter, include everything
        if not frontmatter or "paths" not in frontmatter:
            return True

        # Get the paths patterns from frontmatter
        paths_patterns = frontmatter.get("paths", [])
        if not isinstance(paths_patterns, list):
            paths_patterns = [paths_patterns]

        # Check if any context file matches any of the patterns
        for context_file in self._context_files:
            for pattern in paths_patterns:
                if self._glob_match(context_file, pattern):
                    return True

        # No match found
        return False

    def _glob_match(self, path: str, pattern: str) -> bool:
        """
        Match a path against a glob pattern, supporting ** for recursive directories.

        Args:
            path: The file path to match
            pattern: The glob pattern (e.g., "src/**/*.py")

        Returns:
            True if the path matches the pattern
        """
        # Split pattern into parts
        parts = pattern.split("/")
        path_parts = path.split("/")

        i = 0  # pattern index
        j = 0  # path index

        while i < len(parts) and j < len(path_parts):
            if parts[i] == "**":
                # ** matches zero or more path segments
                if i == len(parts) - 1:
                    # ** at end matches everything remaining
                    return True
                # Try matching the next pattern part at various positions
                for k in range(j, len(path_parts) + 1):
                    if self._glob_match("/".join(path_parts[k:]), "/".join(parts[i+1:])):
                        return True
                return False
            if self._match_segment(path_parts[j] if j < len(path_parts) else "", parts[i]):
                i += 1
                j += 1
            else:
                return False

        # Both should be exhausted for a match
        return i == len(parts) and j == len(path_parts)

    def _match_segment(self, segment: str, pattern: str) -> bool:
        """
        Match a single path segment against a pattern with * and ? wildcards.

        Args:
            segment: The path segment to match
            pattern: The pattern (e.g., "*.py")

        Returns:
            True if the segment matches the pattern
        """
        # Convert glob pattern to regex for single segment
        regex = re.escape(pattern)
        regex = regex.replace(r"\*", "[^/]*")
        regex = regex.replace(r"\?", ".")
        regex = f"^{regex}$"
        return bool(re.match(regex, segment))

    def _process_imports(self, content: str, depth: int) -> str:
        """
        Process @import directives in content, excluding those in code blocks.

        Args:
            content: Content to process
            depth: Current recursion depth

        Returns:
            Content with imports resolved
        """
        # Find all code blocks (both inline and multi-line) to exclude them
        code_blocks = []

        # Find triple-backtick code blocks
        for match in re.finditer(r"```.*?```", content, re.DOTALL):
            code_blocks.append((match.start(), match.end()))

        # Find inline code spans
        for match in re.finditer(r"`[^`]+`", content):
            code_blocks.append((match.start(), match.end()))

        # Find @import patterns
        import_pattern = r"@(~?/?[\w\-./]+(?:\.\w+)?)"

        result = []
        last_end = 0

        for match in re.finditer(import_pattern, content):
            start, end = match.span()

            # Check if this match is inside a code block
            in_code_block = any(block_start <= start < block_end
                              for block_start, block_end in code_blocks)

            if in_code_block:
                # Keep the import as-is if it's in a code block
                continue

            # Add content before the import
            result.append(content[last_end:start])

            # Process the import
            import_path = match.group(1)
            imported_content = self._resolve_and_load_import(import_path, depth + 1)
            result.append(imported_content)

            last_end = end

        # Add remaining content
        result.append(content[last_end:])

        return "".join(result)

    def _resolve_and_load_import(self, import_path: str, depth: int) -> str:
        """
        Resolve an import path and load the file.

        Args:
            import_path: The path from the @import directive
            depth: Current recursion depth

        Returns:
            Content of the imported file
        """
        # Handle home directory paths
        if import_path.startswith("~/"):
            file_path = Path.home() / import_path[2:]
        # Handle absolute paths
        elif import_path.startswith("/"):
            file_path = Path(import_path)
        # Handle relative paths
        else:
            # Use the current directory from the stack
            base_dir = self._path_stack[-1] if self._path_stack else self.project_dir

            file_path = base_dir / import_path

        # If no extension, try common extensions
        if not file_path.suffix:
            for ext in ["", ".md", ".txt", ".json"]:
                test_path = file_path.with_suffix(ext) if ext else file_path
                if test_path.exists():
                    file_path = test_path
                    break

        return self._load_file(file_path, depth)
