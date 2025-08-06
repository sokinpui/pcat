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
    # New file types
    "md": "<!-- {path} -->",
    "json": "// {path}",
    "txt": "# {path}",
    "log": "# {path}",
}
DEFAULT_COMMENT_STYLE = "# {path}"


def _append_file_to_output(file_path, with_paths, output_parts):
    """
    Reads a file and appends its formatted content to the output list.
    Handles I/O errors and prints warnings.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        output_parts.append("```\n")

        if with_paths:
            extension = file_path.suffix.lstrip(".")
            comment_format = COMMENT_STYLES.get(extension, DEFAULT_COMMENT_STYLE)
            comment_line = comment_format.format(path=file_path)
            output_parts.append(f"{comment_line}\n")

        output_parts.append(content)
        output_parts.append("\n```\n\n")
    except IOError as e:
        print(f"Warning: Could not read file {file_path}: {e}", file=sys.stderr)


def parse_arguments(cli_args):
    """
    Parses command-line arguments using argparse.
    """
    parser = argparse.ArgumentParser(
        description="Concatenate files from specified directories or a list of files.",
        epilog="Examples:\n"
        "  pcat -d ./src -d ./lib js ts   # Preferred: Scan directories for extensions\n"
        "  pcat ./src ./lib js ts         # Legacy: Scan directories for extensions\n"
        "  pcat -l ./a.py ./b.sh        # Concatenate a list of files\n"
        "  pcat -d ./src js -l ./c.rs -p # Combine all options\n"
        "  pcat -d ./src any --hidden   # Include hidden files (dotfiles)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--with-paths",
        action="store_true",
        help="Include file paths as comments in the output.",
    )

    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Include hidden files and directories (those starting with a dot).",
    )

    parser.add_argument(
        "-l",
        "--list",
        nargs="+",
        metavar="FILE",
        default=[],
        help="A list of specific files to concatenate.",
    )

    parser.add_argument(
        "-d",
        "--directory",
        action="append",
        metavar="DIR",
        default=[],
        help="A directory to scan. Can be used multiple times. If used, all positional arguments are treated as extensions.",
    )

    parser.add_argument(
        "args",
        nargs="*",
        metavar="ARG",
        help="File extensions or 'any'. If -d is not used, this can be: one or more directories, followed by one or more file extensions.",
    )

    parsed_args = parser.parse_args(cli_args)

    if not parsed_args.directory and not parsed_args.args and not parsed_args.list:
        parser.print_help(sys.stderr)
        sys.exit(1)

    directories_str = []
    extensions = []

    if parsed_args.directory:
        directories_str = parsed_args.directory
        extensions = parsed_args.args
    else:
        if parsed_args.args:
            split_index = len(parsed_args.args)
            for i, arg in enumerate(parsed_args.args):
                if not Path(arg).is_dir():
                    split_index = i
                    break
            directories_str = parsed_args.args[:split_index]
            extensions = parsed_args.args[split_index:]

    if directories_str and not extensions:
        parser.error(
            "Directories were provided, but no file extensions were specified."
        )

    if not directories_str and extensions:
        first_arg = parsed_args.args[0] if parsed_args.args else ""
        parser.error(
            f"No valid directories were provided. The first positional argument '{first_arg}' is not a directory. Use -d to specify directories."
        )

    directories = [Path(d) for d in directories_str]
    for d_path in directories:
        if not d_path.is_dir():
            parser.error(
                f"Directory specified not found or is not a directory: {d_path}"
            )

    listed_files = [Path(f) for f in parsed_args.list]
    for f_path in listed_files:
        if not f_path.is_file():
            parser.error(
                f"File specified in --list not found or is not a file: {f_path}"
            )

    return (
        directories,
        extensions,
        listed_files,
        parsed_args.with_paths,
        parsed_args.hidden,
    )


def generate_output(directories, extensions, listed_files, with_paths, hidden):
    """
    Generates the entire output string in memory before printing.
    """
    output_parts = []
    processed_files = set()

    for i, directory in enumerate(directories):
        output_parts.append(f"{directory}\n---\n")

        found_files_in_dir = set()
        patterns = []
        if "any" in extensions:
            patterns.append("**/*")
        else:
            for ext in extensions:
                clean_ext = ext if ext.startswith(".") else f".{ext}"
                patterns.append(f"**/*{clean_ext}")

        for pattern in patterns:
            found_files_in_dir.update(directory.rglob(pattern))

        # Filter out hidden files/directories unless --hidden is used
        if not hidden:
            filtered_files = set()
            for f in found_files_in_dir:
                # Check if any part of the path relative to the base directory starts with a dot.
                # This correctly handles files like 'project/.git/config' and 'project/.env'.
                if not any(
                    part.startswith(".") for part in f.relative_to(directory).parts
                ):
                    filtered_files.add(f)
            found_files_in_dir = filtered_files

        sorted_files = sorted([f for f in found_files_in_dir if f.is_file()])

        for file_path in sorted_files:
            resolved_path = file_path.resolve()
            if resolved_path not in processed_files:
                _append_file_to_output(file_path, with_paths, output_parts)
                processed_files.add(resolved_path)

        if i < len(directories) - 1:
            if output_parts and output_parts[-1].endswith("\n\n"):
                output_parts[-1] = output_parts[-1][:-2]
            output_parts.append("---\n\n")

    unique_listed_files = [
        f for f in listed_files if f.resolve() not in processed_files
    ]

    if unique_listed_files:
        if directories:
            if output_parts and output_parts[-1].endswith("\n\n"):
                output_parts[-1] = output_parts[-1][:-2]
            output_parts.append("---\n\n")

        output_parts.append("Listed Files\n---\n")
        for file_path in unique_listed_files:
            _append_file_to_output(file_path, with_paths, output_parts)

    return "".join(output_parts)


def run():
    """
    The main entry point for the console script.
    """
    directories, extensions, listed_files, with_paths, hidden = parse_arguments(
        sys.argv[1:]
    )
    full_output = generate_output(
        directories, extensions, listed_files, with_paths, hidden
    )

    try:
        if full_output:
            print(full_output, end="")
    except BrokenPipeError:
        try:
            sys.stderr.close()
        except IOError:
            pass
