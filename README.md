# pcat - Project Content Aggregator Tool

To provide code context for LLM in plain text, especially those unable to parse file other than `.txt` and `.py`. Yes, I am talking about you, Ai studio.

recursively print all files with specified extensions from given directories to stdout.

## Installation

```sh
git clone https://github.com/sokinpui/pcat.git
cd pcat
pipx install .
```

## Usage

### Syntax

```
pcat <dir1> [<dir2>...] <ext1> [<ext2>...]
```

### Example

To print all `.ts`, `.tsx`, and `.css` files from the `frontend/src` directory:

```bash
pcat ./frontend/src ts tsx css
```

To print all Python (`.py`) and Markdown (`.md`) files from the current directory and a `tests/` directory:

```bash
pcat . ./tests py md > project_context.txt
```
