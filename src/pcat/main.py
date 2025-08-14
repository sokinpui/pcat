# src/pcat/main.py
import sys

from .core import CliParser, Pcat


def run():
    """
    The main entry point for the console script.
    """
    try:
        parser = CliParser()
        config = parser.parse(sys.argv[1:])

        app = Pcat(config)
        output = app.run()

        if output:
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
