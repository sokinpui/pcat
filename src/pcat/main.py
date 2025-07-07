# src/pcat/main.py

import sys
from pathlib import Path


# parse_arguments function remains the same...
def parse_arguments(args):
    # ... (no changes needed here) ...
    if not args:
        print("Usage: pcat <dir1> [<dir2>...] <ext1> [<ext2>...]", file=sys.stderr)
        print("Example: pcat ./frontend/src ./backend/api ts tsx js", file=sys.stderr)
        sys.exit(1)
    dirs = []
    exts = []
    split_index = 0
    first_non_dir = None
    for i, arg in enumerate(args):
        if not Path(arg).is_dir():
            split_index = i
            first_non_dir = arg
            break
        split_index = len(args)
    dirs_str = args[:split_index]
    exts = args[split_index:]
    if not dirs_str:
        print("Error: No valid directories were provided.", file=sys.stderr)
        if first_non_dir:
            print(
                f"       The first argument '{first_non_dir}' is not a directory.",
                file=sys.stderr,
            )
        sys.exit(1)
    if not exts:
        print("Error: No file extensions were provided.", file=sys.stderr)
        sys.exit(1)
    return [Path(d) for d in dirs_str], exts


def generate_output(directories, extensions):
    """
    Generates the entire output string in memory before printing.
    """
    # Use a list to collect all parts of the output. Joining a list is
    # much more efficient than concatenating strings with '+='.
    output_parts = []

    for i, directory in enumerate(directories):
        output_parts.append(f"{directory}\n---\n")

        found_files = set()
        for ext in extensions:
            clean_ext = ext if ext.startswith(".") else f".{ext}"
            pattern = f"**/*{clean_ext}"
            found_files.update(directory.rglob(pattern))

        sorted_files = sorted([f for f in found_files if f.is_file()])

        for file_path in sorted_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                output_parts.append("```\n")
                output_parts.append(content)
                output_parts.append("\n```\n\n")  # Add all newlines for spacing
            except IOError as e:
                # Errors are still printed immediately to stderr
                print(f"Warning: Could not read file {file_path}: {e}", file=sys.stderr)

        if i < len(directories) - 1:
            output_parts.append("---\n\n")

    # Join all the pieces and return the final, massive string
    return "".join(output_parts)


def run():
    """
    The main entry point for the console script.
    """
    directories, extensions = parse_arguments(sys.argv[1:])

    # 1. Generate the entire output in memory
    full_output = generate_output(directories, extensions)

    # 2. Print it all in one go
    try:
        print(full_output, end="")
    except BrokenPipeError:
        # This happens if the user pipes the output to a command like `head`
        # and that command closes the pipe early. It's not a real error.
        # We can safely ignore it by closing stderr.
        # See: https://docs.python.org/3/library/signal.html#note-on-sigpipe
        sys.stderr.close()
