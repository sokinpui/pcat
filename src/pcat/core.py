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
 
        if not parsed_args.paths:
            self.parser.print_help(sys.stderr)
            sys.exit(1)
 
        directories: List[Path] = []
        specific_files: List[Path] = []
 
        for path_str in parsed_args.paths:
            path = Path(path_str)
            if path.is_dir():
                directories.append(path)
            elif path.is_file():
                specific_files.append(path)
            else:
                self.parser.error(
                    f"Argument '{path_str}' is not a valid file or directory."
                )
 
        extensions = parsed_args.extension
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
 
    @staticmethod
    def _create_parser() -> argparse.ArgumentParser:
        """Creates and configures the argparse.ArgumentParser instance."""
        parser = argparse.ArgumentParser(
            description="Concatenate and print files from specified paths (files and directories).",
            epilog="Examples:\n"
            "  pcat ./src ./README.md    # Process all files in ./src and the specific file\n"
            "  pcat ./src -e py js       # Process .py and .js files in ./src\n"
            "  pcat file1.txt file2.txt  # Concatenate specific files\n"
            "  pcat . --hidden           # Process all files in current dir, including hidden ones\n"
            "  pcat ./src -e py -n       # Print python files from ./src with line numbers\n"
            "  pcat ./src --list         # List files that would be processed in ./src",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        parser.add_argument(
            "paths",
            nargs="*",
            metavar="PATH",
            help="A list of files and/or directories to process.",
        )
        parser.add_argument(
            "-e",
            "--extension",
            nargs="+",
            action="extend",
            metavar="EXT",
            default=[],
            help="Filter by file extensions (e.g., 'py', 'js'). Applies to directories.",
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
            help="List the files that would be processed, without printing content.",
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
