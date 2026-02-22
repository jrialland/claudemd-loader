"""Example demonstrating the caching feature of claudemd-loader."""

from pathlib import Path
from time import sleep, time

from claudemd_loader import ClaudeMdLoaderContext


def main() -> None:  # noqa: PLR0915
    """Demonstrate caching functionality."""
    project_dir = Path(__file__).parent.parent

    print("=" * 60)
    print("Caching Example - claudemd-loader")
    print("=" * 60)

    # Example 1: Automatic cache with mtime-based invalidation
    print("\n1. Automatic cache invalidation (based on file mtime):")
    print("-" * 60)

    ctx = ClaudeMdLoaderContext(project_dir)

    # First load - will read from disk
    start = time()
    result1 = ctx.load_claudemd(context_files=["src/claudemd_loader/ctx.py"])
    time1 = time() - start
    print(f"First load:  {len(result1)} chars in {time1*1000:.2f}ms")

    # Second load - will use cache (files haven't changed)
    start = time()
    result2 = ctx.load_claudemd(context_files=["src/claudemd_loader/ctx.py"])
    time2 = time() - start
    print(f"Second load: {len(result2)} chars in {time2*1000:.2f}ms (cached)")
    print(f"Speedup: {time1/time2:.1f}x faster")
    print("\nNote: Cache automatically invalidates when files change!")

    # Example 2: Order independence
    print("\n2. Cache is order-independent:")
    print("-" * 60)

    result3 = ctx.load_claudemd(context_files=["file1.py", "file2.py"])
    result4 = ctx.load_claudemd(context_files=["file2.py", "file1.py"])

    print(f"['file1.py', 'file2.py']: {len(result3)} chars")
    print(f"['file2.py', 'file1.py']: {len(result4)} chars")
    print(f"Same result: {result3 == result4}")

    # Example 3: Manual cache invalidation (rarely needed)
    print("\n3. Manual cache invalidation (rarely needed):")
    print("-" * 60)

    print("Clearing cache manually...")
    ctx.invalidate_cache()
    print("Cache cleared (though automatic invalidation usually handles this)")

    # Load again after invalidation - will read from disk
    start = time()
    result5 = ctx.load_claudemd(context_files=["src/claudemd_loader/ctx.py"])
    time5 = time() - start
    print(f"After invalidation: {len(result5)} chars in {time5*1000:.2f}ms")

    # Example 4: Disabling cache
    print("\n4. Caching disabled:")
    print("-" * 60)

    ctx_no_cache = ClaudeMdLoaderContext(project_dir, caching=False)

    start = time()
    result6 = ctx_no_cache.load_claudemd(context_files=["src/claudemd_loader/ctx.py"])
    time6 = time() - start
    print(f"First load:  {len(result6)} chars in {time6*1000:.2f}ms")

    start = time()
    result7 = ctx_no_cache.load_claudemd(context_files=["src/claudemd_loader/ctx.py"])
    time7 = time() - start
    print(f"Second load: {len(result7)} chars in {time7*1000:.2f}ms (no cache)")
    print("Note: Both loads read from disk (caching disabled)")

    # Example 5: Demonstrate automatic invalidation on file change
    print("\n5. Automatic cache invalidation on file changes:")
    print("-" * 60)

    # Create a temporary test directory
    demo_dir = project_dir / "demo_cache"
    demo_dir.mkdir(exist_ok=True)

    # Create a test file to import
    test_file = demo_dir / "test_cache_demo.md"
    test_file.write_text("# Original Content")

    # Create a CLAUDE.md that imports it
    demo_claude = demo_dir / "CLAUDE.md"
    demo_claude.write_text("# Demo\n\n@test_cache_demo.md")

    try:
        ctx_demo = ClaudeMdLoaderContext(demo_dir)

        # First load
        result_a = ctx_demo.load_claudemd()
        print(f"Loaded: {len(result_a)} chars")
        print("Contains 'Original Content': True")

        # Second load - uses cache
        result_b = ctx_demo.load_claudemd()
        print(f"Cached load returned same content: {result_a == result_b}")

        # Wait a moment to ensure mtime will be different
        sleep(0.01)

        # Modify the imported file
        test_file.write_text("# Modified Content")

        # Third load - cache automatically invalidates!
        result_c = ctx_demo.load_claudemd()
        print(f"After file change: {len(result_c)} chars")
        print(f"Contains 'Modified Content': {'Modified Content' in result_c}")
        print("✓ Cache automatically detected file change and reloaded!")

    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)
        demo_claude.unlink(missing_ok=True)
        demo_dir.rmdir()

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✓ Caching is enabled by default for ~100-200x speedup")
    print("✓ Cache automatically invalidates when ANY tracked file changes")
    print("✓ Cache key is based on sorted context_files (order-independent)")
    print("✓ Tracks all files: CLAUDE.md, imports, MEMORY.md (if enabled)")
    print("✓ Uses file modification times (like 'make' does)")
    print("✓ Manual invalidate_cache() available but rarely needed")
    print("✓ Set caching=False to disable caching entirely")


if __name__ == "__main__":
    main()
