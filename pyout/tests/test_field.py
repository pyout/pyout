# -*- coding: utf-8 -*-
import pytest
from pyout.field import Field, StyleProcessors


def test_field_base():
    assert Field()("ok") == "ok        "
    assert Field(width=5, align="right")("ok") == "   ok"


def test_field_update():
    field = Field()
    field.width = 2
    assert field("ok") == "ok"


def test_field_processors():
    def pre(_, result):
        return result.upper()

    def post1(_, result):
        return "AAA" + result

    def post2(_, result):
        return result + "ZZZ"

    field = Field(width=6, align="center")
    field.add("pre", "some_key", pre)
    field.add("post", "another_key", *[post1, post2])
    assert field("ok") == "AAA  OK  ZZZ"

    with pytest.raises(ValueError):
        field.add("not pre or post", "k")


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


def test_style_processor_translate():
    sp = StyleProcessors()
    with pytest.raises(NotImplementedError):
        sp.translate("name")
