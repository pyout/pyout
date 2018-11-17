"""Core pyout interface definitions.
"""

from __future__ import unicode_literals

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class Stream(object):
    """Output stream interface used by Writer.
    """

    @abc.abstractproperty
    def width(self):
        """Maximum line width.
        """

    @abc.abstractmethod
    def write(self, text):
        """Write `text`.
        """

    @abc.abstractmethod
    def clear_last_lines(self, n):
        """Clear previous N lines.
        """

    @abc.abstractmethod
    def overwrite_line(self, n, text):
        """Go to the Nth previous line and overwrite it with `text`
        """

    @abc.abstractmethod
    def move_to(self, n):
        """Move the Nth previous line.
        """
