"""Processor for field value truncation.
"""

from __future__ import unicode_literals


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

    def truncate(self, _, result):
        # TODO: Add an option to center the truncation marker?
        length = self.length
        marker = self.marker

        if len(result) <= length:
            return result
        if marker:
            marker_beg = max(length - len(marker), 0)
            if result[marker_beg:].strip():
                if marker_beg == 0:
                    return marker[:length]
                return result[:marker_beg] + marker
        return result[:length]
