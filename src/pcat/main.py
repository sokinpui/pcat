# src/pcat/main.py

import argparse
import sys
from pathlib import Path

# Dictionary mapping file extensions to their comment syntax.
# The value is a format string where '{path}' will be replaced by the file path.
COMMENT_STYLES = {
    # Scripting & Programming Languages
    "py": "# {path}",
    "sh": "# {path}",
    "rb": "# {path}",
    "pl": "# {path}",
    "js": "// {path}",
    "ts": "// {path}",
    "jsx": "// {path}",
    "tsx": "// {path}",
    "go": "// {path}",
    "java": "// {path}",
    "c": "// {path}",
    "cpp": "// {path}",
    "cs": "// {path}",
    "rs": "// {path}",
    "swift": "// {path}",
    "kt": "// {path}",
    "scala": "// {path}",
    "php": "// {path}",
    "lua": "-- {path}",
    "sql": "-- {path}",
    # Markup & Styling
    "html": "<!-- {path} -->",
    "xml": "<!-- {path} -->",
    "css": "/* {path} */",
    "scss": "/* {path} */",
    # Config & Data
    "yaml": "# {path}",
    "yml": "# {path}",
    "toml": "# {path}",
    "ini": "; {path}",
    "conf": "# {path}",
    "cfg": "# {path}",
}
DEFAULT_COMMENT_STYLE = "// {path}"


def parse_arguments(cli_args):
    """
    Parses command-line arguments using argparse.
    """
    parser = argparse.ArgumentParser(
        description="Concatenate files from specified directories with given extensions.",
        epilog="Example: pcat ./frontend/src ./backend/api ts tsx js",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--with-paths",
        action="store_true",
        help="Include file paths as comments in the output.",
    )

    parser.add_argument(
        "args",
        nargs="*",
        metavar="ARG",
        help="One or more directories, followed by one or more file extensions.",
    )

    parsed_args = parser.parse_args(cli_args)

    if not parsed_args.args:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Separate directories from extensions
    dirs_str = []
    exts = []
    split_index = len(parsed_args.args)
    for i, arg in enumerate(parsed_args.args):
        if not Path(arg).is_dir():
            split_index = i
            break

    dirs_str = parsed_args.args[:split_index]
    exts = parsed_args.args[split_index:]

    if not dirs_str:
        first_arg = parsed_args.args[0] if parsed_args.args else ""
        parser.error(
            f"No valid directories were provided. The first argument '{first_arg}' is not a directory."
        )

    if not exts:
        parser.error("No file extensions were provided.")

    return [Path(d) for d in dirs_str], exts, parsed_args.with_paths


def generate_output(directories, extensions, with_paths):
    """
    Generates the entire output string in memory before printing.
    """
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

                if with_paths:
                    extension = file_path.suffix.lstrip(".")
                    comment_format = COMMENT_STYLES.get(
                        extension, DEFAULT_COMMENT_STYLE
                    )
                    comment_line = comment_format.format(path=file_path)
                    output_parts.append(f"{comment_line}\n")

                output_parts.append(content)
                output_parts.append("\n```\n\n")  # Add all newlines for spacing
            except IOError as e:
                print(f"Warning: Could not read file {file_path}: {e}", file=sys.stderr)

        if i < len(directories) - 1:
            # Trim trailing newlines before adding the separator for cleaner spacing
            if output_parts and output_parts[-1].endswith("\n\n"):
                output_parts[-1] = output_parts[-1][:-2]
            output_parts.append("---\n\n")

    return "".join(output_parts)


def run():
    """
    The main entry point for the console script.
    """
    directories, extensions, with_paths = parse_arguments(sys.argv[1:])

    # 1. Generate the entire output in memory
    full_output = generate_output(directories, extensions, with_paths)

    # 2. Print it all in one go
    try:
        print(full_output, end="")
    except BrokenPipeError:
        # This happens if the user pipes the output to a command like `head`
        # and that command closes the pipe early. It's not a real error.
        try:
            sys.stderr.close()
        except IOError:
            pass
