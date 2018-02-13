# -*- coding: utf-8 -*-
from collections import OrderedDict
from curses import tigetstr, tparm
from functools import partial
from six.moves import StringIO
import sys
import time
import traceback

import blessings
from mock import patch
import pytest

from pyout import Tabular
from pyout.field import StyleFunctionError

# TestTerminal, unicode_cap, and unicode_parm are copied from
# blessings' tests.

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


class AttrData(object):
    """Store `kwargs` as attributes.

    For testing tabular calls to construct row's data from an objects
    attributes.

    This doesn't use __getattr__ to map dict keys to attributes because then
    we'd have to handle a KeyError for the "missing" column tests.
    """
    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_color():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"color": "green", "width": 3}},
                  stream=fd, force_styling=True)
    out({"name": "foo"})

    expected = unicode_parm("setaf", COLORNUMS["green"]) + "foo" + \
               unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_empty_string():
    fd = StringIO()
    out = Tabular(stream=fd)
    out({"name": ""})
    assert eq_repr(fd.getvalue(), "\n")


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_missing_column():
    fd = StringIO()
    out = Tabular(columns=["name", "status"], stream=fd)
    out({"name": "solo"})
    assert eq_repr(fd.getvalue(), "solo \n")


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_missing_column_missing_text():
    fd = StringIO()
    out = Tabular(columns=["name", "status"],
                  style={"status":
                         {"missing": "-"}},
                  stream=fd)
    out({"name": "solo"})
    assert eq_repr(fd.getvalue(), "solo -\n")


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_list_value():
    fd = StringIO()
    out = Tabular(columns=["name", "status"], stream=fd)
    out({"name": "foo", "status": [0, 1]})
    assert eq_repr(fd.getvalue(), "foo [0, 1]\n")


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_missing_column_missing_object_data():
    data = AttrData(name="solo")

    fd = StringIO()
    out = Tabular(columns=["name", "status"],
                  style={"status":
                         {"missing": "-"}},
                  stream=fd)
    out(data)
    assert eq_repr(fd.getvalue(), "solo -\n")


@patch("pyout.tabular.Terminal", TestTerminal)
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
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_columns_orderdict_mapping(row):
    fd = StringIO()
    out = Tabular(OrderedDict([("name", "Long name"),
                               ("status", "Status")]),
                  style={"header_": {},
                         "name": {"width": 10},
                         "status": {"width": 6}},
                  stream=fd)

    out(row)

    expected = ("Long name  Status\n"
                "foo        ok    \n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
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


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_header():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"header_": {},
                         "name": {"width": 10},
                         "status": {"width": 10}},
                  stream=fd, force_styling=True)
    out({"name": "foo",
         "status": "installed"})
    out({"name": "bar",
         "status": "installed"})

    expected = ("name       status    \n"
                "foo        installed \n"
                "bar        installed \n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_data_as_object():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"width": 3},
                         "status": {"width": 9}},
                  stream=fd)

    out(AttrData(name="foo", status="installed"))
    out(AttrData(name="bar", status="unknown"))

    expected = "foo installed\nbar unknown  \n"
    assert fd.getvalue() == expected


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_different_data_types_same_output():
    style = {"header_": {},
             "name": {"width": 10},
             "status": {"width": 10}}

    fd_list = StringIO()
    out_list = Tabular(["name", "status"], style=style, stream=fd_list)

    fd_dict = StringIO()
    out_dict = Tabular(["name", "status"], style=style, stream=fd_dict)

    fd_od = StringIO()
    out_od = Tabular(style=style, stream=fd_od)

    out_list(["foo", "installed"])
    out_list(["bar", "installed"])

    out_dict({"name": "foo", "status": "installed"})
    out_dict({"name": "bar", "status": "installed"})

    out_od(OrderedDict([("name", "foo"),
                        ("status", "installed")]))
    out_od(OrderedDict([("name", "bar"),
                        ("status", "installed")]))

    assert fd_dict.getvalue() == fd_list.getvalue()
    assert fd_dict.getvalue() == fd_od.getvalue()


@patch("pyout.tabular.Terminal", TestTerminal)
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


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_nondefault_separator():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"header_": {},
                         "separator_": " | ",
                         "name": {"width": 4},
                         "status": {"width": 9}},
                  stream=fd)
    out({"name": "foo",
         "status": "installed"})
    out({"name": "bar",
         "status": "installed"})

    expected = ("name | status   \n"
                "foo  | installed\n"
                "bar  | installed\n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_data_as_list_no_columns():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"width": 9}},
                  stream=fd)
    with pytest.raises(ValueError):
        out(["foo", "installed"])


@patch("pyout.tabular.Terminal", TestTerminal)
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


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_default_style():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"default_": {"width": 3}},
                  stream=fd)
    out({"name": "foo", "status": "OK"})
    out({"name": "bar", "status": "OK"})

    expected = ("foo OK \n"
                "bar OK \n")
    assert fd.getvalue() == expected


@patch("pyout.tabular.Terminal", TestTerminal)
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


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_align():
    fd = StringIO()
    out = Tabular(["name"],
                  style={"name": {"align": "right", "width": 10}},
                  stream=fd, force_styling=True)
    out({"name": "foo"})

    assert eq_repr(fd.getvalue(), "       foo\n")


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"width": 3}, "status": {"width": 9}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)

    out.rewrite({"name": "foo"}, {"status": "installed"})

    expected = unicode_cap("cuu1") * 2 + unicode_cap("el") + "foo installed"
    assert eq_repr(fd.getvalue().strip().splitlines()[-1],
                   expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite_notfound():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)

    with pytest.raises(ValueError):
        out.rewrite({"name": "not here"}, {"status": "installed"},
                    style={"name": {"width": 3},
                           "status": {"width": 9}})


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite_multi_id():
    fd = StringIO()
    out = Tabular(["name", "type", "status"],
                  style={"name": {"width": 3},
                         "type": {"width": 1},
                         "status": {"width": 9}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "type": "0", "status": "unknown"},
            {"name": "foo", "type": "1", "status": "unknown"},
            {"name": "bar", "type": "2", "status": "installed"}]
    for row in data:
        out(row)

    out.rewrite({"name": "foo", "type": "0"}, {"status": "installed"})

    expected = unicode_cap("cuu1") * 3 + unicode_cap("el") + "foo 0 installed"
    assert eq_repr(fd.getvalue().strip().splitlines()[-1],
                   expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite_multi_value():
    fd = StringIO()
    out = Tabular(["name", "type", "status"],
                  style={"name": {"width": 3},
                         "type": {"width": 1},
                         "status": {"width": 9}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "type": "0", "status": "unknown"},
            {"name": "bar", "type": "1", "status": "unknown"}]
    for row in data:
        out(row)

    out.rewrite({"name": "foo"}, {"status": "installed", "type": "3"})

    expected = unicode_cap("cuu1") * 2 + unicode_cap("el") + "foo 3 installed"
    assert eq_repr(fd.getvalue().strip().splitlines()[-1],
                   expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite_with_ids_property():
    def write():
        data = [{"name": "foo", "type": "0", "status": "unknown"},
                {"name": "foo", "type": "1", "status": "unknown"},
                {"name": "bar", "type": "2", "status": "installed"}]

        fd = StringIO()
        out = Tabular(["name", "type", "status"],
                      style={"name": {"width": 3},
                             "type": {"width": 1},
                             "status": {"width": 9}},
                      stream=fd, force_styling=True)
        for row in data:
            out(row)
        return fd, out

    fd_param, out_param = write()
    fd_prop, out_prop = write()
    out_prop.ids = ["name", "type"]

    assert eq_repr(fd_param.getvalue(), fd_prop.getvalue())

    out_param.rewrite({"name": "foo", "type": "0"}, {"status": "installed"})
    out_prop.rewrite(["foo", "0"], {"status": "installed"})

    assert eq_repr(fd_param.getvalue(), fd_prop.getvalue())


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite_auto_width():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"width": 3}, "status": {"width": "auto"}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "unknown"},
            {"name": "baz", "status": "unknown"}]
    for row in data:
        out(row)

    out.rewrite({"name": "bar"}, {"status": "installed"})

    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo unknown  ")]) == 1
    assert len([ln for ln in lines if ln.endswith("baz unknown  ")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_rewrite_data_as_list():
    def init():
        fd = StringIO()
        out = Tabular(["name", "status"],
                      style={"name": {"width": 3},
                             "status": {"width": 9}},
                      stream=fd)
        return fd, out

    fd_list, out_list = init()
    out_list(["foo", "unknown"])
    out_list(["bar", "installed"])
    out_list.rewrite({"name": "foo"}, {"status": "installed"})

    fd_dict, out_dict = init()
    out_dict({"name": "foo", "status": "unknown"})
    out_dict({"name": "bar", "status": "installed"})
    out_dict.rewrite({"name": "foo"}, {"status": "installed"})

    assert fd_list.getvalue() == fd_dict.getvalue()


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_repaint():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"width": 3},
                         "status": {"width": 9}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)
    out._repaint()

    lines = fd.getvalue().splitlines()
    assert len(lines) == 2 * len(data)
    assert unicode_cap("el") + "bar installed" in lines


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_repaint_with_header():
    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"header_": {},
                         "name": {"width": 4},
                         "status": {"width": 9}},
                  stream=fd, force_styling=True)
    data = [{"name": "foo", "status": "unknown"},
            {"name": "bar", "status": "installed"}]
    for row in data:
        out(row)
    out._repaint()

    lines = fd.getvalue().splitlines()

    assert len(lines) == 2 * (len(data) + 1)
    assert unicode_cap("el") + "bar  installed" in lines

    header = unicode_cap("cuu1") * 3 + unicode_cap("el") + "name status   "
    assert header in lines


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_lookup_color():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"color": {"lookup": {"BAD": "red"}},
                                    "width": 6}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("status", "OK")]))
    out(OrderedDict([("name", "bar"),
                     ("status", "BAD")]))

    expected = "foo " + "OK    \n" + \
               "bar " + unicode_parm("setaf", COLORNUMS["red"]) + \
               "BAD   " + unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_lookup_bold():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"bold": {"lookup": {"BAD": True}},
                                    "width": 6}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("status", "OK")]))
    out(OrderedDict([("name", "bar"),
                     ("status", "BAD")]))

    expected = "foo " + "OK    \n" + \
               "bar " + unicode_cap("bold") + \
               "BAD   " + unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_lookup_bold_false():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"bold": {"lookup": {"BAD": False}},
                                    "width": 6}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("status", "OK")]))
    out(OrderedDict([("name", "bar"),
                     ("status", "BAD")]))

    expected = ("foo OK    \n"
                "bar BAD   \n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_lookup_non_hashable():
    fd = StringIO()
    out = Tabular(style={"status": {"color": {"lookup": {"BAD": "red"}}}},
                  stream=fd)
    out(OrderedDict([("status", [0, 1])]))
    expected = ("[0, 1]\n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_intervals_color():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "percent": {"color": {"interval":
                                               [[0, 50, "red"],
                                                [50, 80, "yellow"],
                                                [80, 100, "green"]]},
                                     "width": 7}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("percent", 88)]))
    out(OrderedDict([("name", "bar"),
                     ("percent", 33)]))

    expected = "foo " + unicode_parm("setaf", COLORNUMS["green"]) + \
               "88     " + unicode_cap("sgr0") + "\n" + \
               "bar " + unicode_parm("setaf", COLORNUMS["red"]) + \
               "33     " + unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_intervals_color_open_ended():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "percent": {"color": {"interval":
                                               [[None, 50, "red"],
                                                [80, None, "green"]]},
                                     "width": 7}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("percent", 88)]))
    out(OrderedDict([("name", "bar"),
                     ("percent", 33)]))

    expected = "foo " + unicode_parm("setaf", COLORNUMS["green"]) + \
               "88     " + unicode_cap("sgr0") + "\n" + \
               "bar " + unicode_parm("setaf", COLORNUMS["red"]) + \
               "33     " + unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_intervals_color_outside_intervals():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "percent": {"color": {"interval":
                                               [[0, 50, "red"]]},
                                     "width": 7}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("percent", 88)]))
    out(OrderedDict([("name", "bar"),
                     ("percent", 33)]))

    expected = "foo 88     \n" + \
               "bar " + unicode_parm("setaf", COLORNUMS["red"]) + \
               "33     " + unicode_cap("sgr0") + "\n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_intervals_bold():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "percent": {"bold": {"interval":
                                              [[30, 50, False],
                                               [50, 80, True]]},
                                     "width": 2}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("percent", 78)]))
    out(OrderedDict([("name", "bar"),
                     ("percent", 33)]))

    expected = "foo " + unicode_cap("bold") + \
               "78" + unicode_cap("sgr0") + "\n" + \
               "bar 33\n"
    assert eq_repr(fd.getvalue(), expected)



@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_intervals_missing():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "percent": {"bold": {"interval":
                                              [[30, 50, False],
                                               [50, 80, True]]},
                                     "width": 2}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("percent", 78)]))
    # Interval lookup function can handle a missing value.
    out(OrderedDict([("name", "bar")]))

    expected = "foo " + unicode_cap("bold") + \
               "78" + unicode_cap("sgr0") + "\n" + \
               "bar   \n"
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_transform():
    fd = StringIO()
    out = Tabular(style={"val": {"transform": lambda x: x[::-1]}},
                  stream=fd)
    out(OrderedDict([("name", "foo"),
                     ("val", "330")]))
    out(OrderedDict([("name", "bar"),
                     ("val", "780")]))

    expected = ("foo 033\n"
                "bar 087\n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_transform_with_header():
    fd = StringIO()
    out = Tabular(style={"header_": {},
                         "name": {"width": 4},
                         "val": {"transform": lambda x: x[::-1]}},
                  stream=fd)
    out(OrderedDict([("name", "foo"),
                     ("val", "330")]))
    out(OrderedDict([("name", "bar"),
                     ("val", "780")]))

    expected = ("name val\n"
                "foo  033\n"
                "bar  087\n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_transform_autowidth():
    fd = StringIO()
    out = Tabular(style={"val": {"transform": lambda x: x * 2}},
                  stream=fd)
    out(OrderedDict([("name", "foo"),
                     ("val", "330")]))
    out(OrderedDict([("name", "bar"),
                     ("val", "7800")]))

    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo 330330  ")]) == 1
    assert len([ln for ln in lines if ln.endswith("bar 78007800")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_transform_on_header():
    fd = StringIO()
    out = Tabular(style={"header_": {"transform": str.upper},
                         "name": {"width": 4},
                         "val": {"width": 3}},
                  stream=fd)
    out(OrderedDict([("name", "foo"),
                     ("val", "330")]))
    out(OrderedDict([("name", "bar"),
                     ("val", "780")]))

    expected = ("NAME VAL\n"
                "foo  330\n"
                "bar  780\n")
    assert eq_repr(fd.getvalue(), expected)


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_transform_func_error():
    def dontlikeints(x):
        return x[::-1]

    fd = StringIO()
    out = Tabular(style={"name": {"width": 4},
                         "val": {"transform": dontlikeints}},
                  stream=fd)
    # The transform function receives the data as given, so it fails trying to
    # index an integer.
    try:
        out(OrderedDict([("name", "foo"), ("val", 330)]))
    except:
        exc_type, value, tb = sys.exc_info()
        try:
            assert isinstance(value, StyleFunctionError)
            tblines = "\n".join(
                traceback.format_exception(exc_type, value, tb))
            assert "in dontlikeints" in tblines
        finally:
            del tb


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_width_truncate_long():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 8},
                         "status": {"width": 3}},
                  stream=fd)
    out(OrderedDict([("name", "abcdefghijklmnop"),
                     ("status", "OK"),]))
    out(OrderedDict([("name", "bar"),
                     ("status", "BAD"),]))

    expected = ("abcde... OK \n"
                "bar      BAD\n")
    assert fd.getvalue() == expected


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth():
    fd = StringIO()
    out = Tabular(style={"name": {"width": "auto"},
                         "status": {"width": "auto"},
                         "path": {"width": 6}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "fooab"),
                     ("status", "OK"),
                     ("path", "/tmp/a")]))
    out(OrderedDict([("name", "bar"),
                     ("status", "BAD"),
                     ("path", "/tmp/b")]))

    lines = fd.getvalue().splitlines()
    assert "bar   BAD /tmp/b" in lines
    assert len([ln for ln in lines if ln.endswith("fooab OK  /tmp/a")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth_with_header():
    fd = StringIO()
    out = Tabular(style={"header_": {},
                         "name": {"width": "auto"},
                         "status": {"width": "auto"}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foobar"),
                     ("status", "OK")]))
    out(OrderedDict([("name", "baz"),
                     ("status", "OK")]))

    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("name   status")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth_min():
    fd = StringIO()
    out = Tabular(style={"name": {"width": "auto"},
                         "status": {"width": {"auto": True, "min": 5}},
                         "path": {"width": 6}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "fooab"),
                     ("status", "OK"),
                     ("path", "/tmp/a")]))
    out(OrderedDict([("name", "bar"),
                     ("status", "BAD"),
                     ("path", "/tmp/b")]))

    lines = fd.getvalue().splitlines()
    assert "bar   BAD   /tmp/b" in lines
    assert len([ln for ln in lines if ln.endswith("fooab OK    /tmp/a")]) == 1


@pytest.mark.parametrize("marker", [True, False, u"…"],
                         ids=["marker=True", "marker=False", u"marker=…"])
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth_min_max(marker):
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"width":
                                    {"auto": True, "min": 2, "max": 7}},
                         "path": {"width": {"auto": True, "max": 5,
                                            "marker": marker}}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("status", "U"),
                     ("path", "/tmp/a")]))

    if marker is True:
        assert fd.getvalue() == "foo U  /t...\n"
    elif marker:
        assert fd.getvalue() == u"foo U  /tmp…\n"
    else:
        assert fd.getvalue() == "foo U  /tmp/\n"

    out(OrderedDict([("name", "bar"),
                     ("status", "BAD!!!!!!!!!!!"),
                     ("path", "/tmp/b")]))

    lines = fd.getvalue().splitlines()
    if marker is True:
        assert len([ln for ln in lines if ln.endswith("foo U       /t...")]) == 1
        assert len([ln for ln in lines if ln.endswith("bar BAD!... /t...")]) == 1
    elif marker:
        assert len([ln for ln in lines if ln.endswith(u"foo U       /tmp…")]) == 1
        assert len([ln for ln in lines if ln.endswith(u"bar BAD!... /tmp…")]) == 1
    else:
        assert len([ln for ln in lines if ln.endswith("foo U       /tmp/")]) == 1
        assert len([ln for ln in lines if ln.endswith("bar BAD!... /tmp/")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth_min_max_with_header():
    fd = StringIO()
    out = Tabular(style={"header_": {},
                         "name": {"width": 4},
                         "status": {"width":
                                    {"auto": True, "min": 2, "max": 8}}},
                  stream=fd, force_styling=True)
    out(OrderedDict([("name", "foo"),
                     ("status", "U")]))

    lines0 = fd.getvalue().splitlines()
    assert len([ln for ln in lines0 if ln.endswith("name status")]) == 1
    assert len([ln for ln in lines0 if ln.endswith("foo  U     ")]) == 1

    out(OrderedDict([("name", "bar"),
                     ("status", "BAD!!!!!!!!!!!")]))

    lines1 = fd.getvalue().splitlines()
    assert len([ln for ln in lines1 if ln.endswith("bar  BAD!!...")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth_different_data_types_same_output():
    fd_dict = StringIO()
    out_dict = Tabular(["name", "status"],
                       style={"header_": {},
                              "name": {"width": 4},
                              "status": {"width":
                                         {"auto": True, "min": 2, "max": 8}}},
                       stream=fd_dict)
    out_dict({"name": "foo", "status": "U"})
    out_dict({"name": "bar", "status": "BAD!!!!!!!!!!!"})

    fd_list = StringIO()
    out_list = Tabular(["name", "status"],
                       style={"header_": {},
                              "name": {"width": 4},
                              "status": {"width":
                                         {"auto": True, "min": 2, "max": 8}}},
                       stream=fd_list)
    out_list(["foo", "U"])
    out_list(["bar", "BAD!!!!!!!!!!!"])

    assert fd_dict.getvalue() == fd_list.getvalue()


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_autowidth_auto_false_exception():
    fd = StringIO()
    out = Tabular(style={"header_": {},
                         "name": {"width": 4},
                         "status": {"width": {"auto": False}}},
                  stream=fd, force_styling=True)
    with pytest.raises(ValueError):
        out(OrderedDict([("name", "foo"),
                         ("status", "U")]))


class Delayed(object):
    """Helper for producing a delayed callable.
    """

    def __init__(self, value):
        self.value = value
        self.now = False

    def run(self):
        """Return `value` once `now` is true.
        """
        while True:
            if self.now:
                return self.value


@pytest.mark.timeout(10)
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_callable_values():
    delay0 = Delayed("done")
    delay1 = Delayed("over")

    fd = StringIO()
    with Tabular(["name", "status"], stream=fd, force_styling=True) as out:
        out({"name": "foo", "status": ("thinking", delay0.run)})
        out({"name": "bar", "status": "ok"})
        # A single callable can be passed rather than (initial_value, fn).
        out({"name": "baz", "status": delay1.run})

        expected = ("foo thinking\n"
                    "bar ok      \n"
                    "baz         \n")
        assert eq_repr(fd.getvalue(), expected)

        delay0.now = True
        delay1.now = True
    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo done    ")]) == 1
    assert len([ln for ln in lines if ln.endswith("baz over    ")]) == 1


@pytest.mark.timeout(10)
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_callable_transform_nothing():
    delay0 = Delayed(3)

    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"status": {"transform": lambda n: n + 2}},
                  stream=fd)
    with out:
        # The unspecified initial value is set to Nothing().  The transform
        # function above, which is designed to take a number, won't be called
        # with it.
        out({"name": "foo", "status": delay0.run})
        assert eq_repr(fd.getvalue(), "foo \n")
        delay0.now = True
    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo 5")]) == 1


@pytest.mark.timeout(10)
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_callable_values_multi_return():
    delay = Delayed({"status": "done", "path": "/tmp/a"})

    fd = StringIO()
    out = Tabular(["name", "status", "path"], stream=fd, force_styling=True)
    with out:
        out({"name": "foo", ("status", "path"): ("...", delay.run)})
        out({"name": "bar", "status": "ok", "path": "na"})

        expected = ("foo ... ...\n"
                    "bar ok  na \n")
        assert eq_repr(fd.getvalue(), expected)

        delay.now = True
    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo done /tmp/a")]) == 1


@pytest.mark.timeout(10)
@pytest.mark.parametrize("result",
                         [{"status": "done", "path": "/tmp/a"},
                          ("done", "/tmp/a")],
                         ids=["result=tuple", "result=dict"])
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_callable_values_multicol_key_infer_column(result):
    delay = Delayed(result)
    fd = StringIO()
    out = Tabular(stream=fd, force_styling=True)
    with out:
        out(OrderedDict([("name", "foo"),
                         (("status", "path"), ("...", delay.run))]))
        out(OrderedDict([("name", "bar"),
                         ("status", "ok"),
                         ("path", "na")]))

        expected = ("foo ... ...\n"
                    "bar ok  na \n")
        assert eq_repr(fd.getvalue(), expected)

        delay.now = True
    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo done /tmp/a")]) == 1


def delayed_gen_func(*values):
    if not values:
        values = ["update", "finished"]

    def fn():
        for val in values:
            time.sleep(0.05)
            yield val
    return fn


@pytest.mark.timeout(10)
@pytest.mark.parametrize("gen_source",
                         [delayed_gen_func(),
                          delayed_gen_func()()],
                         ids=["gen_func", "generator"])
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_generator_function_values(gen_source):
    fd = StringIO()
    with Tabular(["name", "status"], stream=fd) as out:
        out({"name": "foo", "status": ("waiting", gen_source)})
        out({"name": "bar", "status": "ok"})

        expected = ("foo waiting\n"
                    "bar ok     \n")
        assert eq_repr(fd.getvalue(), expected)
    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo update ")]) == 1
    assert len([ln for ln in lines if ln.endswith("foo finished")]) == 1
    assert len([ln for ln in lines if ln.endswith("bar ok      ")]) == 1


@pytest.mark.timeout(10)
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_generator_values_multireturn():
    gen = delayed_gen_func({"status": "working"},  # for one of two columns
                           {"path": "/tmp/a"},  # for the other of two columns
                           {"path": "/tmp/b",  # for both columns
                            "status": "done"})
    fd = StringIO()
    out = Tabular(stream=fd)
    with out:
        out(OrderedDict([("name", "foo"),
                         (("status", "path"), ("...", gen))]))
        out(OrderedDict([("name", "bar"),
                         ("status", "ok"),
                         ("path", "na")]))

        expected = ("foo ... ...\n"
                    "bar ok  na \n")
        assert eq_repr(fd.getvalue(), expected)
    lines = fd.getvalue().splitlines()
    assert len([ln for ln in lines if ln.endswith("foo working ...")]) == 1
    assert len([ln for ln in lines if ln.endswith("foo working /tmp/a")]) == 1
    assert len([ln for ln in lines if ln.endswith("foo done    /tmp/b")]) == 1


@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_wait_noop_if_nothreads():
    fd = StringIO()
    with Tabular(["name", "status"], stream=fd, force_styling=True) as out:
        out({"name": "foo", "status": "done"})
        out({"name": "bar", "status": "ok"})

        expected = ("foo done\n"
                    "bar ok  \n")
        assert eq_repr(fd.getvalue(), expected)


@pytest.mark.timeout(10)
@pytest.mark.parametrize("form", ["dict", "list", "attrs"])
@patch("pyout.tabular.Terminal", TestTerminal)
def test_tabular_write_delayed(form):
    data = OrderedDict([("name", "foo"),
                        ("paired0", 1),
                        ("paired1", 2),
                        ("solo", 3)])

    if form == "dict":
        row = data
    elif form == "list":
        row = list(data.values())
    elif form == "attrs":
        row = AttrData(**data)

    fd = StringIO()
    out = Tabular(list(data.keys()),
                  style={"paired0": {"delayed": "pair"},
                         "paired1": {"delayed": "pair"},
                         "solo": {"delayed": True}},
                  stream=fd)
    with out:
        out(row)
    lines = fd.getvalue().splitlines()
    assert lines[0] == "foo   "

    # Either paired0/paired1 came in first or solo came in first, but
    # paired0/paired1 should arrive together.
    firstin = [ln for ln in lines
               if ln.endswith("foo 1 2 ") or ln.endswith("foo   3")]
    assert len(firstin) == 1

    assert lines[-1].endswith("foo 1 2 3")
