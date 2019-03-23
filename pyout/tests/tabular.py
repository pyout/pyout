"""A Tabular for testing.
"""

from __future__ import unicode_literals

from mock import patch

from six.moves import StringIO

from pyout import Tabular as TheRealTabular
from pyout.tests.terminal import Terminal


class Tabular(TheRealTabular):
    """Test-specific subclass of pyout.Tabular.

    Like pyout.Tabular but `stream` is set to a StringIO object that reports to
    be interactive.  Its value is accessible via the `stdout` property.
    """

    def __init__(self, *args, **kwargs):
        stream = kwargs.pop("stream", None)
        if not stream:
            stream = StringIO()
            stream.isatty = lambda: True
        with patch("pyout.tabular.Terminal", Terminal):
            super(Tabular, self).__init__(
                *args, stream=stream, **kwargs)

    @property
    def stdout(self):
        return self._stream.stream.getvalue()
