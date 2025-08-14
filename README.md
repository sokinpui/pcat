# pcat - Project Content Aggregator Tool

A tool to concatenate source code from multiple directories and files, tailored for providing context to Large Language Models (LLMs). Don't relay on `upload files` feature of LLM providers' web UI. Why AI studio doesn't support `.js` files upload?

```
usage: pcat [-h] [-n] [--hidden] [-f FILE [FILE ...]] [-l] [-d DIR [DIR ...]]
            [-e EXT [EXT ...]]
            [ARG ...]

Concatenate files from specified directories or a list of files.

positional arguments:
  ARG                   Legacy support for positional arguments (directories followed by extensions). Not allowed when using -d or -e.

options:
  -h, --help            show this help message and exit
  -n, --with-line-numbers
                        Include line numbers for each file.
  --hidden              Include hidden files and directories (those starting with a dot).
  -f, --file FILE [FILE ...]
                        A list of specific files to concatenate.
  -l, --list            List the files that would be processed, without printing content.
  -d, --directory DIR [DIR ...]
                        One or more directories to scan.
  -e, --extension EXT [EXT ...]
                        One or more file extensions to include (e.g., 'py', 'js'). Defaults to 'any' if -d is used without -e.

Examples:
  # Recommended usage with flags:
  pcat -d ./src                  # Scan ./src for all file types
  pcat -d ./src -e py js       # Scan ./src for .py and .js files
  pcat -d ./src ./lib -e py    # Scan ./src and ./lib for .py files
  pcat -f ./a.py ./b.sh        # Concatenate a specific list of files
  pcat -d ./src -e js -f ./c.rs # Combine directory, extension, and file flags
  pcat -d ./src --hidden         # Include hidden files (dotfiles) in scan
  pcat -d ./src -e py -n         # Print python files with line numbers

  # Legacy usage (for backward compatibility):
  pcat ./src js ts             # Scan ./src for .js and .ts files

```
