# src/pcat/main.py
import subprocess
import sys

from .core import CliParser, Pcat


def copy_to_clipboard(text: str):
    """Copies text to the system clipboard using native tools."""
    if not text:
        return

    commands = []
    if sys.platform == "darwin":
        commands.append(["pbcopy"])
    elif sys.platform == "linux":
        commands.append(["xclip", "-selection", "clipboard"])
        commands.append(["xsel", "--clipboard", "--input"])
    elif sys.platform == "win32":
        commands.append(["clip"])
    else:
        print(
            f"pcat: Clipboard functionality not supported on {sys.platform}.",
            file=sys.stderr,
        )
        sys.exit(1)

    for command in commands:
        try:
            subprocess.run(
                command,
                input=text.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("pcat: Copied to clipboard.", file=sys.stderr)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    tool_name = "xclip or xsel" if sys.platform == "linux" else commands[0][0]
    print(f"pcat: {tool_name} not found. Please install it to use this feature.", file=sys.stderr)
    sys.exit(1)


def run():
    """
    The main entry point for the console script.
    """
    try:
        parser = CliParser()
        config = parser.parse(sys.argv[1:])

        app = Pcat(config)
        output = app.run()

        if config.to_clipboard:
            copy_to_clipboard(output)
        elif output:
            print(output, end="")
    except BrokenPipeError:
        # This occurs when piping output to a command like `head`, which
        # may close the pipe before pcat has finished writing.
        try:
            # This helps prevent a 'Broken pipe' error message from being
            # printed to the console.
            sys.stderr.close()
        except IOError:
            pass
