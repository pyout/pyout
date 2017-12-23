from collections import OrderedDict
from curses import tigetstr, tparm
from functools import partial
from six.moves import StringIO

import blessings
from mock import patch
import pytest

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


def eq_repr(a, b):
    """Compare the repr's of `a` and `b` to escape escape codes.
    """
    return repr(a) == repr(b)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_color():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"color": "green", "width": 3}},
                  stream=fd, force_styling=True)
    out({"name": "foo"})

    expected = unicode_parm("setaf", COLORNUMS["green"]) + "foo" + \
               unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_columns_from_orderdict_row():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "id": {"width": 3},
                         "status": {"width": 9},
                         "path": {"width": 8}},
                  stream=fd)

    row = OrderedDict([("name", "foo"),
                       ("id", "001"),
                       ("status", "installed"),
                       ("path", "/tmp/foo")])
    out(row)

    assert eq_repr(fd.getvalue(), "foo 001 installed /tmp/foo\n")


@pytest.mark.parametrize("row", [["foo", "ok"],
                                 {"name": "foo", "status": "ok"}],
                         ids=["sequence", "dict"])
@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_columns_orderdict_mapping(row):
    fd = StringIO()
    out = Tabular(OrderedDict([("name", "Long name"),
                               ("status", "Status")]),
                  style={"header_": {}},
                  stream=fd)

    out(row)

    expected = ("Long name  Status    \n"
                "foo        ok        \n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_data_as_list():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"width": 3},
                         "status": {"width": 9}},
                  stream=fd)
    out(["foo", "installed"])
    out(["bar", "unknown"])

    expected = "foo installed\nbar unknown  \n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_header():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"header_": {}},
                  stream=fd, force_styling=True)
    out({"name": "foo",
         "status": "installed"})
    out({"name": "bar",
         "status": "installed"})

    expected = ("name       status    \n"
                "foo        installed \n"
                "bar        installed \n"    )
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_header_with_style():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"header_": {"underline": True},
                         "name": {"width": 4},
                         "status": {"width": 9,
                                    "color": "green"}},
                  stream=fd, force_styling=True)
    out({"name": "foo",
         "status": "installed"})

    expected = unicode_cap("smul") + "name" + unicode_cap("sgr0") + " " + \
               unicode_cap("smul") + "status   " + unicode_cap("sgr0") + \
               "\nfoo  " + unicode_parm("setaf", COLORNUMS["green"]) + \
               "installed" + unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_data_as_list_no_columns():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"width": 9}},
                  stream=fd)
    with pytest.raises(ValueError):
        out(["foo", "installed"])


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_style_override():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"color": "green", "width": 3}},
                  stream=fd, force_styling=True)
    out({"name": "foo"},
        style={"name": {"color": "black", "width": 3}})

    expected = unicode_parm("setaf", COLORNUMS["black"]) + "foo" + \
               unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_multicolor():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"color": "green", "width": 3},
                         "status": {"color": "white", "width": 7}},
                  stream=fd, force_styling=True)
    out({"name": "foo", "status": "unknown"})

    expected = unicode_parm("setaf", COLORNUMS["green"]) + "foo" + \
               unicode_cap("sgr0") + " " + \
               unicode_parm("setaf", COLORNUMS["white"]) + "unknown" + \
               unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_align():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"align": ">", "width": 10}},
                  stream=fd, force_styling=True)
    out({"name": "foo"})

    assert eq_repr(fd.getvalue(), "       foo\n")


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_update():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)

    out.rewrite({"name": "foo"}, "status", "installed",
                style = {"name": {"width": 3},
                         "status": {"width": 9}})

    expected = unicode_cap("cuu1") * 2 + unicode_cap("el") + "foo installed"
    assert eq_repr(fd.getvalue().strip().splitlines()[-1],
                   expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_update_notfound():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)

    with pytest.raises(ValueError):
        out.rewrite({"name": "not here"}, "status", "installed",
                    style = {"name": {"width": 3},
                             "status": {"width": 9}})


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_update_multi_id():
    fd = StringIO()
    out = Tabular(["name", "type", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "type": "0", "status": "unknown"},
            {"name": "foo", "type": "1", "status": "unknown"},
            {"name": "bar", "type": "2", "status": "installed"}]
    for row in data:
        out(row)

    out.rewrite({"name": "foo", "type": "0"},
                "status", "installed",
                style = {"name": {"width": 3},
                         "type": {"width": 1},
                         "status": {"width": 9}})

    expected = unicode_cap("cuu1") * 3 + unicode_cap("el") + "foo 0 installed"
    assert eq_repr(fd.getvalue().strip().splitlines()[-1],
                   expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_repaint():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)
    out._repaint()

    msg = ("foo        unknown   \n"
           "bar        installed \n")
    expected = msg + unicode_cap("clear") + msg
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.Terminal", TestTerminal)
def test_tabular_repaint_with_header():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"header_": {}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)
    out._repaint()

    msg = ("name       status    \n"
           "foo        unknown   \n"
           "bar        installed \n")
    expected = msg + unicode_cap("clear") + msg
    assert eq_repr(fd.getvalue(), expected)
