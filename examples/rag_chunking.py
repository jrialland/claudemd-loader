"""
Example demonstrating RAG chunking functionality.

This example shows how to use load_claudemd_chunks() to generate text chunks
for vector databases or RAG (Retrieval-Augmented Generation) systems.
"""

from pathlib import Path

from claudemd_loader import ClaudeMdLoaderContext


print("RAG Chunking Example")
print("=" * 50)
print()

# Setup test project context
project_dir = Path(__file__).parent.parent.resolve()
ctx = ClaudeMdLoaderContext(project_dir)

print("Example 1: Basic Chunking")
print("-" * 50)
print("Splitting CLAUDE.md files into 200-character chunks:")
print()

# Generate chunks (defaults: chunk_size=200, chunk_overlap=0)
chunks_generator = ctx.load_claudemd_chunks(chunk_size=200)

for i, (file_path, text, start_line, end_line) in enumerate(chunks_generator):
    filename = Path(file_path).name
    # Show first 50 chars of chunk...
    preview = text[:50].replace("\n", " ") + "..."
    print(f"Chunk {i + 1}: {filename} (lines {start_line}-{end_line})")
    print(f"  Length: {len(text)} chars")
    print(f"  Content: {preview}")
    print()

    # Just show first 3 chunks
    if i >= 2:
        print("... (stopping output)")
        break

print()
print("Example 2: Overlapping Chunks")
print("-" * 50)
print("Splitting with 50-character overlap (better for RAG context preservation):")
print()

# Generate overlapping chunks
overlapping_chunks = ctx.load_claudemd_chunks(chunk_size=200, chunk_overlap=50)

for i, (file_path, text, start_line, end_line) in enumerate(overlapping_chunks):
    if i >= 2:
        break

    filename = Path(file_path).name
    print(f"Chunk {i + 1}: {filename} (lines {start_line}-{end_line})")
    print(f"  Start: {text[:20].replace(chr(10), ' ')}...")
    print(f"  End:   ...{text[-20:].replace(chr(10), ' ')}")
    print()

print("Example 3: Targeted Loading")
print("-" * 50)
print("Loading chunks only for specific context files:")
print()

# Typically used when you want chunks relevant to specific source code
# This filters which CLAUDE.md files are loaded based on their frontmatter
chunks = list(
    ctx.load_claudemd_chunks(context_files=["src/claudemd_loader/ctx.py"], chunk_size=500)
)

print(f"Generated {len(chunks)} chunks for context: src/claudemd_loader/ctx.py")
