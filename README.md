# pcat - Project Content Aggregator Tool

A tool to concatenate source code from multiple directories and files, tailored for providing context to Large Language Models (LLMs). Don't relay on `upload files` feature of LLM providers' web UI. Why AI studio doesn't support `.js` files upload?

## Features

- Recursively scan multiple directories for files with specific extensions.
- Concatenate an explicit list of individual files.
- Combine directory scanning and file listing in a single command.
- Optionally prepend each file's content with its path, commented out in the correct syntax for its file type.
- Intelligently groups output by source directory.
- Gracefully handles read errors and ignores unreadable files.

## Installation

```sh
git clone https://github.com/sokinpui/pcat.git
cd pcat
pipx install .
```

## Usage

The primary way to use `pcat` is by specifying directories to scan and file extensions to include. You can also add specific files and enable path comments.

### Syntax

```sh
pcat [-d DIR]... [EXTS]... [-l FILE]... [-p]
```

- `-d, --directory DIR`: A directory to scan. Can be used multiple times. Positional arguments that follow are treated as file extensions.
- `-l, --list FILE`: A list of specific files to concatenate.
- `-p, --with-paths`: Include file paths as comments at the top of each file's content.

### Examples

**1. Scan a Directory for Specific File Types**

To print all `.ts`, `.tsx`, and `.css` files from the `frontend/src` directory:

```bash
pcat -d ./frontend/src ts tsx css
```

_Output format:_

```md
### SOURCE CODE

<file>
// content of a .ts file
</file>

<file>
/* content of a .css file */
</file>

...

### SOURCE CODE END
```

**2. Scan Multiple Directories and Add File Paths**

To print all Python (`.py`) files from the `src/` and `tests/` directories, with path comments included, and save to a file:

```bash
pcat -p -d ./src -d ./tests py > project_context.txt
```

**3. Concatenate a Specific List of Files**

To print the contents of `a.py` and `b.sh` regardless of their location:

```bash
pcat -l ./a.py ./b.sh
```

**4. Combine Directory Scanning and Listed Files**

You can mix and match all options. Here, we scan the `src` directory for `.js` files, add the project's `README.md`, and include path comments for all of them:

```bash
pcat -p -d ./src js -l ./README.md
```
