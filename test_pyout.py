from curses import tigetstr, tparm
from functools import partial
from six.moves import StringIO

import blessings
from mock import patch

from pyout import _adopt, Tabular


def test_adopt_noop():
    default_value = {"align": "<",
                     "width": 10,
                     "attrs": []}

    style = {"name": default_value,
             "path": default_value,
             "status": default_value}

    newstyle = _adopt(style, None)
    for key, value in style.items():
        assert newstyle[key] == value


def test_adopt():
    default_value = {"align": "<",
                     "width": 10,
                     "attrs": []}

    style = {"name": default_value,
             "path": default_value,
             "status": default_value}

    newstyle = _adopt(style, {"path": {"width": 99},
                              "status": {"attrs": ["foo"]}})
    for key, value in style.items():
        if key == "path":
            expected = {"align": "<", "width": 99, "attrs": []}
            assert newstyle[key] == expected
        elif key == "status":
            expected = {"align": "<", "width": 10, "attrs": ["foo"]}
            assert newstyle[key] == expected
        else:
            assert newstyle[key] == value

### Tabular tests

## TestTerminal, unicode_cap, and unicode_parm are copied from
## blessings' tests.

TestTerminal = partial(blessings.Terminal, kind='xterm-256color')


def unicode_cap(cap):
    """Return the result of ``tigetstr`` except as Unicode."""
    return tigetstr(cap).decode('latin1')


def unicode_parm(cap, *parms):
    """Return the result of ``tparm(tigetstr())`` except as Unicode."""
    return tparm(tigetstr(cap), *parms).decode('latin1')


COLORNUMS = {"black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4,
             "magenta": 5, "cyan": 6, "white": 7}


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_color():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"attrs": ["green"], "width": 3}},
                  stream=fd, force_styling=True)
    out.write({"name": "foo"})

    expected = unicode_parm("setaf", COLORNUMS["green"]) + "foo" + \
               unicode_cap("sgr0") + "\n"
    assert fd.getvalue() == expected


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_multicolor():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"attrs": ["green"], "width": 3},
                         "status": {"attrs": ["white"], "width": 7}},
                  stream=fd, force_styling=True)
    out.write({"name": "foo", "status": "unknown"})

    expected = unicode_parm("setaf", COLORNUMS["green"]) + "foo" + \
               unicode_cap("sgr0") + " " + \
               unicode_parm("setaf", COLORNUMS["white"]) + "unknown" + \
               unicode_cap("sgr0") + "\n"

    assert fd.getvalue() == expected


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_align():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"align": ">", "width": 10}},
                  stream=fd, force_styling=True)
    out.write({"name": "foo"})

    assert fd.getvalue() == "       foo\n"


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_update():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "path": "/tmp/foo", "status": "unknown"},
            {"name": "bar", "path": "/tmp/bar", "status": "installed"}]
    for row in data:
        out.write(row)

    out.rewrite("foo", "status", "installed",
                style = {"name": {"width": 3},
                         "status": {"width": 9}})

    expected = unicode_cap("cuu1") * 2 + unicode_cap("el") + "foo installed"
    assert fd.getvalue().strip().splitlines()[-1] == expected


@patch("pyout.Terminal", TestTerminal)
def test_tabular_repaint():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out.write(row)
    out._repaint()

    msg = ("foo        unknown   \n"
           "bar        installed \n")
    expected = msg + unicode_cap("clear") + msg
    assert fd.getvalue() == expected
