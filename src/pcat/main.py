# src/pcat/main.py
import argparse
import sys
from pathlib import Path


def _append_file_to_output(file_path, with_paths, output_parts):
    """
    Reads a file and appends its formatted content to the output list.
    Handles I/O errors and prints warnings.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        if with_paths:
            output_parts.append(f'<file path="{file_path}">\n')
        else:
            output_parts.append("<file>\n")

        output_parts.append(content)

        if not content.endswith("\n"):
            output_parts.append("\n")

        output_parts.append("</file>\n\n")
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
        "  pcat -d ./src js -l ./c.rs -p # Combine all options, adding path attributes\n"
        "  pcat -d ./src any --hidden   # Include hidden files (dotfiles)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--with-paths",
        action="store_true",
        help="Include file paths as a 'path' attribute in the <file> tag.",
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
    processed_files = set()
    files_to_process = []

    # Gather files from directories
    for directory in directories:
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
                if not any(
                    part.startswith(".") for part in f.relative_to(directory).parts
                ):
                    filtered_files.add(f)
            found_files_in_dir = filtered_files

        files_to_process.extend(sorted([f for f in found_files_in_dir if f.is_file()]))

    # Add listed files
    files_to_process.extend(listed_files)

    # Create a final, unique list of files to process
    final_files = []
    for file_path in files_to_process:
        resolved_path = file_path.resolve()
        if resolved_path not in processed_files:
            final_files.append(file_path)
            processed_files.add(resolved_path)

    if not final_files:
        return ""

    output_parts = ["### SOURCE CODE ###\n\n"]

    for file_path in final_files:
        _append_file_to_output(file_path, with_paths, output_parts)

    # Clean up trailing newlines and add the end marker
    if len(output_parts) > 1:
        # Remove final two newlines from the last file entry
        if output_parts[-1].endswith("\n\n"):
            output_parts[-1] = output_parts[-1][:-1]
        output_parts.append("### SOURCE CODE END ###\n")

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
