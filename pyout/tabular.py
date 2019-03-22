"""Interface for styling tabular terminal output.

This module defines the Tabular entry point.
"""

from __future__ import unicode_literals

from contextlib import contextmanager
from logging import getLogger

from blessings import Terminal

from pyout import interface
from pyout.field import TermProcessors

lgr = getLogger(__name__)


class TerminalStream(interface.Stream):
    """Stream interface implementation using blessings.Terminal.
    """

    def __init__(self, stream=None, interactive=None):
        super(TerminalStream, self).__init__(
            stream=stream, interactive=interactive)
        self.term = Terminal(stream=stream,
                             # interactive=False maps to force_styling=None.
                             force_styling=self.interactive or None)
        self._height = None

    @property
    def width(self):
        """Maximum terminal width.
        """
        if self.interactive:
            return self.term.width

    @property
    def height(self):
        """Terminal height.
        """
        if self.interactive:
            if self._height is None:
                self._height = self.term.height
            return self._height

    def write(self, text):
        """Write `text` to terminal.
        """
        self.term.stream.write(text)

    def clear_last_lines(self, n):
        """Clear last N lines of terminal output.
        """
        self.term.stream.write(
            self.term.move_up * n + self.term.clear_eos)
        self.term.stream.flush()

    @contextmanager
    def _moveback(self, n):
        self.term.stream.write(self.term.move_up * n + self.term.clear_eol)
        try:
            yield
        finally:
            self.term.stream.write(self.term.move_down * (n - 1))
            self.term.stream.flush()

    def overwrite_line(self, n, text):
        """Move back N lines and overwrite line with `text`.
        """
        with self._moveback(n):
            self.term.stream.write(text)

    def move_to(self, n):
        """Move back N lines in terminal.
        """
        self.term.stream.write(self.term.move_up * n)


class Tabular(interface.Writer):
    """Interface for writing and updating styled terminal output.

    Parameters
    ----------
    columns : list of str or OrderedDict, optional
        Column names.  An OrderedDict can be used instead of a sequence to
        provide a map of short names to the displayed column names.

        If not given, the keys will be extracted from the first row of data
        that the object is called with, which is particularly useful if the row
        is an OrderedDict.  This argument must be given if this instance will
        not be called with a mapping.
    style : dict, optional
        Each top-level key should be a column name and the value should be a
        style dict that overrides the `default_style` class attribute.  See the
        "Examples" section below.
    stream : stream object, optional
        Write output to this stream (sys.stdout by default).
    interactive : boolean, optional
        Whether stream is considered interactive.  By default, this is
        determined by calling `stream.isatty()`.  If non-interactive, the bold,
        color, and underline keys will be ignored, and the mode will default to
        "final".

    Examples
    --------

    Create a `Tabular` instance for two output fields, "name" and
    "status".

    >>> out = Tabular(["name", "status"], style={"status": {"width": 5}})

    The first field, "name", is taken as the unique ID.  The `style` argument
    is used to override the default width for the "status" field that is
    defined by the class attribute `default_style`.

    Write a row to stdout:

    >>> out({"name": "foo", "status": "OK"})

    Write another row, overriding the style:

    >>> out({"name": "bar", "status": "BAD"},
    ...     style={"status": {"color": "red", "bold": True}})
    """

    def __init__(self, columns=None, style=None, stream=None,
                 interactive=None):
        super(Tabular, self).__init__(columns, style, stream=stream,
                                      interactive=interactive)
        streamer = TerminalStream(stream=stream, interactive=interactive)
        if streamer.interactive:
            processors = TermProcessors(streamer.term)
        else:
            processors = None
        super(Tabular, self)._init(style, streamer, processors)
