# -*- coding: utf-8 -*-
from collections import OrderedDict
from curses import tigetstr, tparm
from functools import partial
from six.moves import StringIO

import blessings
from mock import patch
import pytest

from pyout import _adopt, Field, StyleProcessors, Tabular


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
             "status": default_value,
             "sep_": "non-mapping"}

    newstyle = _adopt(style, {"path": {"width": 99},
                              "status": {"attrs": ["foo"]},
                              "sep_": "non-mapping update"})
    for key, value in style.items():
        if key == "path":
            expected = {"align": "<", "width": 99, "attrs": []}
            assert newstyle[key] == expected
        elif key == "status":
            expected = {"align": "<", "width": 10, "attrs": ["foo"]}
            assert newstyle[key] == expected
        elif key == "sep_":
            assert newstyle[key] == "non-mapping update"
        else:
            assert newstyle[key] == value


def test_field_base():
    assert Field()("ok") == "ok        "
    assert Field(width=5, align="right")("ok") == "   ok"


def test_field_update():
    field = Field()
    field.width = 2
    assert field("ok") == "ok"


def test_field_processors():
    field = Field(width=6, align="center")

    def proc1(_, result):
        return "AAA" + result

    def proc2(_, result):
        return result + "ZZZ"

    field.processors["default"] = [proc1, proc2]

    assert field("ok") == "AAA  ok  ZZZ"


def test_truncate_mark_true():
    fn = StyleProcessors.truncate(7, marker=True)

    assert fn(None, "abc") == "abc"
    assert fn(None, "abcdefg") == "abcdefg"
    assert fn(None, "abcdefgh") == "abcd..."


def test_truncate_mark_string():
    fn = StyleProcessors.truncate(7, marker=u"…")

    assert fn(None, "abc") == "abc"
    assert fn(None, "abcdefg") == "abcdefg"
    assert fn(None, "abcdefgh") == u"abcdef…"


def test_truncate_mark_short():
    fn = StyleProcessors.truncate(2, marker=True)
    assert fn(None, "abc") == ".."


def test_truncate_nomark():
    fn = StyleProcessors.truncate(7, marker=False)

    assert fn(None, "abc") == "abc"
    assert fn(None, "abcdefg") == "abcdefg"
    assert fn(None, "abcdefgh") == "abcdefg"


def test_style_value_type():
    fn = StyleProcessors.value_type

    assert fn(True) == "simple"
    assert fn("red") == "simple"
    assert fn({"label": {"BAD": "red"}}) == "label"

    interval = {"interval": [(0, 50, "red"), (50, 80, "yellow")]}
    assert fn(interval) == "interval"

    with pytest.raises(ValueError):
        fn({"unknown": 1})

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
                  style={"header_": {},
                         "name": {"width": 10},
                         "status": {"width": 6}},
                  stream=fd)

    out(row)

    expected = ("Long name  Status\n"
                "foo        ok    \n")
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


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_data_as_object():
    class Data(object):
        def __init__(self, data):
            self._data = data

        def __getattr__(self, name):
            return self._data[name]


    fd = StringIO()
    out = Tabular(["name", "status"],
                  style={"name": {"width": 3},
                         "status": {"width": 9}},
                  stream=fd)

    out(Data({"name": "foo", "status": "installed"}))
    out(Data({"name": "bar", "status": "unknown"}))

    expected = "foo installed\nbar unknown  \n"
    assert fd.getvalue() == expected


@patch("pyout.Terminal", TestTerminal)
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
                  style={"name": {"align": "right", "width": 10}},
                  stream=fd, force_styling=True)
    out({"name": "foo"})

    assert eq_repr(fd.getvalue(), "       foo\n")


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_label_color():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"color": {"label": {"BAD": "red"}},
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


@patch("pyout.Terminal", TestTerminal)
def test_tabular_write_label_bold():
    fd = StringIO()
    out = Tabular(style={"name": {"width": 3},
                         "status": {"bold": {"label": {"BAD": True}},
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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
@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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


@patch("pyout.Terminal", TestTerminal)
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
