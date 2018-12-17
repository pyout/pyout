"""Processor for field value truncation.
"""

from __future__ import unicode_literals


def _truncate_right(value, length, marker):
    if len(value) <= length:
        short = value
    elif marker:
        nchars_free = length - len(marker)
        if nchars_free > 0:
            short = value[:nchars_free] + marker
        else:
            short = marker[:length]
    else:
        short = value[:length]
    return short


class Truncater(object):
    """A processor that truncates the result to a given length.

    Note: You probably want to place the `truncate` method at the beginning of
    the processor list so that the truncation is based on the length of the
    original value.

    Parameters
    ----------
    length : int
        Truncate the string to this length.
    marker : str or bool, optional
        Indicate truncation with this string.  If True, indicate truncation by
        replacing the last three characters of a truncated string with '...'.
        If False, no truncation marker is added to a truncated string.
    """

    def __init__(self, length, marker=True):
        self.length = length
        self.marker = "..." if marker is True else marker
        self._truncate_fn = _truncate_right

    def truncate(self, _, result):
        return self._truncate_fn(result, self.length, self.marker)
