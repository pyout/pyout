"""Not much of an interface for styling tabular terminal output.

This module defines a mostly useless Tabular entry point.  Previous lines are
not updated, and the results are not styled (e.g., no coloring or bolding of
values).  In other words, this is not a real attempt to support Windows.
"""

from __future__ import unicode_literals

import sys

from pyout import interface


class NoUpdateTerminalStream(interface.Stream):

    supports_updates = False

    def __init__(self, stream=None):
        self.stream = stream or sys.stdout

    def _die(self, *args, **kwargs):
        raise NotImplementedError("{!s} does not support 'update' methods"
                                  .format(self.__class__.__name__))

    clear_last_lines = _die
    overwrite_line = _die
    move_to = _die

    # Height and width are the fallback defaults of py3's
    # shutil.get_terminal_size().

    @property
    def width(self):
        return 80

    @property
    def height(self):
        return 24

    def write(self, text):
        self.stream.write(text)


class Tabular(interface.Writer):
    """Like `pyout.tabular.Tabular`, but broken.

    This doesn't support terminal styling or updating previous content.
    """

    def __init__(self, columns=None, style=None):
        super(Tabular, self).__init__(columns, style)
        streamer = NoUpdateTerminalStream()
        super(Tabular, self)._init(style, streamer)
