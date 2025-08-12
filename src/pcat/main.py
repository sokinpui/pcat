# src/pcat/main.py
import argparse
import sys
from pathlib import Path


def _append_file_to_output(file_path, with_paths, with_line_numbers, output_parts):
    """
    Reads a file and appends its formatted content to the output list.
    Handles I/O errors and prints warnings.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        if with_paths:
            output_parts.append(f"`{file_path}`\n")

        if with_line_numbers:
            lines = content.splitlines()
            content = "\n".join(f"{i+1: >4} | {line}" for i, line in enumerate(lines))

        # get the extension of the file
        ext = file_path.suffix[1:] if file_path.suffix else "txt"
        output_parts.append(f"```{ext}\n")
        output_parts.append(content)

        if not content.endswith("\n"):
            output_parts.append("\n")

        output_parts.append("```\n\n")
    except IOError as e:
        print(f"Warning: Could not read file {file_path}: {e}", file=sys.stderr)


def parse_arguments(cli_args):
    """
    Parses command-line arguments using argparse.
    """
    parser = argparse.ArgumentParser(
        description="Concatenate or list files from specified directories or a list of files.",
        epilog="Examples:\n"
        "  pcat -d ./src -d ./lib js ts   # Preferred: Scan directories for extensions\n"
        "  pcat ./src ./lib js ts         # Legacy: Scan directories for extensions\n"
        "  pcat -f ./a.py ./b.sh        # Concatenate a list of files\n"
        "  pcat -d ./src js -f ./c.rs -p # Combine all options, adding path attributes\n"
        "  pcat -d ./src any --hidden   # Include hidden files (dotfiles)\n"
        "  pcat -d ./src py -n          # Print python files with line numbers\n"
        "  pcat -d ./src py -l          # List python files instead of printing content",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--with-paths",
        action="store_true",
        help="Include file paths as a 'path' attribute in the <file> tag.",
    )

    parser.add_argument(
        "-n",
        "--with-line-numbers",
        action="store_true",
        help="Include line numbers for each file.",
    )

    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Include hidden files and directories (those starting with a dot).",
    )

    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_only",
        help="List the files that would be processed, without printing their content.",
    )

    parser.add_argument(
        "-f",
        "--file",
        nargs="+",
        metavar="FILE",
        dest="file_list",
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

    if not parsed_args.directory and not parsed_args.args and not parsed_args.file_list:
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

    listed_files = [Path(f) for f in parsed_args.file_list]
    for f_path in listed_files:
        if not f_path.is_file():
            parser.error(
                f"File specified in --file not found or is not a file: {f_path}"
            )

    return (
        directories,
        extensions,
        listed_files,
        parsed_args.with_paths,
        parsed_args.hidden,
        parsed_args.with_line_numbers,
        parsed_args.list_only,
    )


def _collect_files(directories, extensions, listed_files, hidden):
    """
    Gathers and returns a unique, sorted list of files to be processed.
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

    # Create a final, unique list of files to process, preserving order for listed files
    final_files = []
    for file_path in files_to_process:
        resolved_path = file_path.resolve()
        if resolved_path not in processed_files:
            final_files.append(file_path)
            processed_files.add(resolved_path)

    return final_files


def generate_output(final_files, with_paths, with_line_numbers):
    """
    Generates the entire output string in memory before printing.
    """
    if not final_files:
        return ""

    output_parts = ["### SOURCE CODE ###\n\n"]

    for file_path in final_files:
        _append_file_to_output(file_path, with_paths, with_line_numbers, output_parts)

    # Clean up trailing newlines and add the end marker
    if len(output_parts) > 1:
        # Remove final two newlines from the last file entry
        if output_parts[-1].endswith("\n\n"):
            output_parts[-1] = output_parts[-1][:-1]
        output_parts.append("\n### SOURCE CODE END ###\n")

    return "".join(output_parts)


def run():
    """
    The main entry point for the console script.
    """
    (
        directories,
        extensions,
        listed_files,
        with_paths,
        hidden,
        with_line_numbers,
        list_only,
    ) = parse_arguments(sys.argv[1:])

    final_files = _collect_files(directories, extensions, listed_files, hidden)

    if list_only:
        if final_files:
            print("\n".join(str(f) for f in final_files))
        return

    full_output = generate_output(final_files, with_paths, with_line_numbers)

    try:
        if full_output:
            print(full_output, end="")
    except BrokenPipeError:
        try:
            sys.stderr.close()
        except IOError:
            pass
