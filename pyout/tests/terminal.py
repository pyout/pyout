"""Terminal test utilities.
"""

from __future__ import unicode_literals

from curses import tigetstr
from curses import tparm
from functools import partial
import re

import blessings

from pyout.tests.utils import assert_contains


class Terminal(blessings.Terminal):

    def __init__(self, *args, **kwargs):
        super(Terminal, self).__init__(
            *args, kind="xterm-256color", **kwargs)

    @property
    def width(self):
        return 100

    @property
    def height(self):
        return 20


# unicode_cap, and unicode_parm are copied from blessings' tests.


def unicode_cap(cap):
    """Return the result of ``tigetstr`` except as Unicode."""
    return tigetstr(cap).decode('latin1')


def unicode_parm(cap, *parms):
    """Return the result of ``tparm(tigetstr())`` except as Unicode."""
    return tparm(tigetstr(cap), *parms).decode('latin1')


COLORNUMS = {"black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4,
             "magenta": 5, "cyan": 6, "white": 7}


def capres(name, value):
    """Format value with CAP key, followed by a reset.
    """
    if name in COLORNUMS:
        prefix = unicode_parm("setaf", COLORNUMS[name])
    else:
        prefix = unicode_cap(name)
    return prefix + value + unicode_cap("sgr0")


def eq_repr_noclear(actual, expected):
    """Like `eq_repr`, but strip clear-related codes from `actual`.
    """
    clear_codes = [re.escape(unicode_cap(x)) for x in ["el", "ed", "cuu1"]]
    match = re.match("(?:{}|{}|{})*(.*)".format(*clear_codes), actual)
    assert match, "This should always match"
    return repr(match.group(1)) == repr(expected)


assert_contains_nc = partial(assert_contains, cmp=eq_repr_noclear)
