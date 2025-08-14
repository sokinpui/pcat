# src/pcat/core.py
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, TextIO


@dataclass(frozen=True)
class PcatConfig:
    """Immutable configuration for the pcat tool."""
    directories: List[Path] = field(default_factory=list)
    extensions: List[str] = field(default_factory=list)
    specific_files: List[Path] = field(default_factory=list)
    with_line_numbers: bool = False
    hidden: bool = False
    list_only: bool = False


class CliParser:
    """Parses command-line arguments into a PcatConfig object."""

    def __init__(self):
        self.parser = self._create_parser()

    def parse(self, cli_args: List[str]) -> PcatConfig:
        """Parses arguments and performs validation, returning a config object."""
        parsed_args = self.parser.parse_args(cli_args)

        has_opts = parsed_args.directory or parsed_args.extension
        has_legacy_args = parsed_args.args
        has_files = parsed_args.file

        if not has_opts and not has_legacy_args and not has_files:
            self.parser.print_help(sys.stderr)
            sys.exit(1)

        if has_opts and has_legacy_args:
            self.parser.error(
                "Positional arguments for directories/extensions are not allowed when using -d or -e."
            )

        directories_str: List[str] = []
        extensions: List[str] = []

        if has_opts:
            directories_str = parsed_args.directory
            extensions = parsed_args.extension
        elif has_legacy_args:
            # Legacy mode: split positional args into dirs and exts
            split_index = len(parsed_args.args)
            for i, arg in enumerate(parsed_args.args):
                if not Path(arg).is_dir():
                    split_index = i
                    break
            directories_str.extend(parsed_args.args[:split_index])
            extensions.extend(parsed_args.args[split_index:])

            if not directories_str and extensions:
                self.parser.error(
                    f"In legacy mode, the first argument '{parsed_args.args[0]}' is not a directory. Use -d to specify directories."
                )

        directories = self._validate_directories(directories_str)
        specific_files = self._validate_files(parsed_args.file)

        if directories and not extensions:
            # Default to all file types if directories are given but extensions are not.
            extensions = ["any"]

        return PcatConfig(
            directories=directories,
            extensions=extensions,
            specific_files=specific_files,
            hidden=parsed_args.hidden,
            with_line_numbers=parsed_args.with_line_numbers,
            list_only=parsed_args.list,
        )

    def _validate_directories(self, dir_paths: List[str]) -> List[Path]:
        """Validates that directory paths exist and are directories."""
        validated_paths = []
        for d_str in dir_paths:
            d_path = Path(d_str)
            if not d_path.is_dir():
                self.parser.error(
                    f"Directory not found or is not a directory: {d_path}"
                )
            validated_paths.append(d_path)
        return validated_paths

    def _validate_files(self, file_paths: List[str]) -> List[Path]:
        """Validates that file paths exist and are files."""
        validated_paths = []
        for f_str in file_paths:
            f_path = Path(f_str)
            if not f_path.is_file():
                self.parser.error(
                    f"File specified in --file not found or is not a file: {f_path}"
                )
            validated_paths.append(f_path)
        return validated_paths

    @staticmethod
    def _create_parser() -> argparse.ArgumentParser:
        """Creates and configures the argparse.ArgumentParser instance."""
        parser = argparse.ArgumentParser(
            description="Concatenate files from specified directories or a list of files.",
            epilog="Examples:\n"
            "  # Recommended usage with flags:\n"
            "  pcat -d ./src                  # Scan ./src for all file types\n"
            "  pcat -d ./src -e py js       # Scan ./src for .py and .js files\n"
            "  pcat -d ./src ./lib -e py    # Scan ./src and ./lib for .py files\n"
            "  pcat -f ./a.py ./b.sh        # Concatenate a specific list of files\n"
            "  pcat -d ./src -e js -f ./c.rs # Combine directory, extension, and file flags\n"
            "  pcat -d ./src --hidden         # Include hidden files (dotfiles) in scan\n"
            "  pcat -d ./src -e py -n         # Print python files with line numbers\n\n"
            "  # Legacy usage (for backward compatibility):\n"
            "  pcat ./src js ts             # Scan ./src for .js and .ts files",
            formatter_class=argparse.RawTextHelpFormatter,
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
            "-f",
            "--file",
            nargs="+",
            metavar="FILE",
            default=[],
            help="A list of specific files to concatenate.",
        )
        parser.add_argument(
            "-l",
            "--list",
            action="store_true",
            help="List the files that would be processed, without printing content.",
        )
        parser.add_argument(
            "-d",
            "--directory",
            nargs="+",
            action="extend",
            metavar="DIR",
            default=[],
            help="One or more directories to scan.",
        )
        parser.add_argument(
            "-e",
            "--extension",
            nargs="+",
            action="extend",
            metavar="EXT",
            default=[],
            help="One or more file extensions to include (e.g., 'py', 'js'). Defaults to 'any' if -d is used without -e.",
        )
        parser.add_argument(
            "args",
            nargs="*",
            metavar="ARG",
            help="Legacy support for positional arguments (directories followed by extensions). Not allowed when using -d or -e.",
        )
        return parser


class FileFinder:
    """Finds files based on directory scanning configuration."""

    def __init__(self, config: PcatConfig):
        self.config = config

    def find(self) -> List[Path]:
        """Scans directories and returns a sorted list of file paths."""
        all_files: Set[Path] = set()
        for directory in self.config.directories:
            all_files.update(self._find_in_directory(directory))
        return sorted(list(all_files))

    def _find_in_directory(self, directory: Path) -> Set[Path]:
        """Finds files within a single directory."""
        patterns = self._get_glob_patterns()
        found_files: Set[Path] = set()
        for pattern in patterns:
            found_files.update(directory.rglob(pattern))

        if not self.config.hidden:
            found_files = self._filter_hidden(found_files, directory)

        return {f for f in found_files if f.is_file()}

    def _get_glob_patterns(self) -> List[str]:
        """Gets glob patterns from extensions."""
        if "any" in self.config.extensions:
            return ["**/*"]
        return [
            f"**/*{ext if ext.startswith('.') else f'.{ext}'}"
            for ext in self.config.extensions
        ]

    @staticmethod
    def _filter_hidden(files: Set[Path], base_dir: Path) -> Set[Path]:
        """Removes files located in hidden directories or that are hidden themselves."""
        filtered = set()
        for f in files:
            try:
                relative_parts = f.relative_to(base_dir).parts
                if not any(part.startswith(".") for part in relative_parts):
                    filtered.add(f)
            except ValueError:
                continue
        return filtered


class OutputFormatter:
    """Formats a list of files into a single string for output."""

    def __init__(self, config: PcatConfig):
        self.config = config

    def format(self, files: List[Path], writer: TextIO = sys.stderr) -> str:
        """Creates the final formatted string from a list of files."""
        if not files:
            return ""

        output_parts = ["### SOURCE CODE ###\n\n"]
        for file_path in files:
            self._format_file(file_path, output_parts, writer)

        if len(output_parts) > 1:
            if output_parts[-1].endswith("\n\n"):
                output_parts[-1] = output_parts[-1][:-1]
            output_parts.append("\n### SOURCE CODE END ###\n")

        return "".join(output_parts)

    def _format_file(self, file_path: Path, output_parts: List[str], writer: TextIO):
        """Formats a single file and appends it to the output list."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            output_parts.append(f"`{file_path}`\n")

            if self.config.with_line_numbers:
                lines = content.splitlines()
                content = "\n".join(
                    f"{i+1: >4} | {line}" for i, line in enumerate(lines)
                )

            ext = file_path.suffix[1:] if file_path.suffix else "txt"
            output_parts.append(f"```{ext}\n")
            output_parts.append(content)

            if not content.endswith("\n"):
                output_parts.append("\n")

            output_parts.append("```\n\n")
        except IOError as e:
            print(f"Warning: Could not read file {file_path}: {e}", file=writer)


class Pcat:
    """The main pcat application orchestrator."""

    def __init__(self, config: PcatConfig):
        self.config = config

    def run(self) -> str:
        """Executes the file finding and formatting process."""
        finder = FileFinder(self.config)
        directory_files = finder.find()

        all_files = self._deduplicate_files(
            directory_files + self.config.specific_files
        )

        if self.config.list_only:
            return "\n".join(map(str, all_files)) + ("\n" if all_files else "")

        formatter = OutputFormatter(self.config)
        return formatter.format(all_files)

    @staticmethod
    def _deduplicate_files(files: List[Path]) -> List[Path]:
        """Removes duplicate files while preserving order."""
        processed_paths: Set[Path] = set()
        unique_files: List[Path] = []
        for file_path in files:
            resolved_path = file_path.resolve()
            if resolved_path not in processed_paths:
                unique_files.append(file_path)
                processed_paths.add(resolved_path)
        return unique_files
