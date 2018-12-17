# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pytest

from pyout.truncate import _splice as splice
from pyout.truncate import Truncater


def test_splice_non_positive():
    with pytest.raises(ValueError):
        assert splice("", 0)


def test_splice():
    assert splice("", 10) == ("", "")
    assert splice("abc", 10) == ("a", "bc")
    assert splice("abc", 3) == ("a", "bc")
    assert splice("abcefg", 3) == ("a", "fg")


def test_truncate_mark_true():
    fn = Truncater(7, marker=True).truncate

    assert fn(None, "abc") == "abc"
    assert fn(None, "abcdefg") == "abcdefg"
    assert fn(None, "abcdefgh") == "abcd..."


def test_truncate_mark_string():
    fn = Truncater(7, marker="…").truncate

    assert fn(None, "abc") == "abc"
    assert fn(None, "abcdefg") == "abcdefg"
    assert fn(None, "abcdefgh") == "abcdef…"


def test_truncate_mark_short():
    fn = Truncater(2, marker=True).truncate
    assert fn(None, "abc") == ".."


def test_truncate_nomark():
    fn = Truncater(7, marker=False).truncate

    assert fn(None, "abc") == "abc"
    assert fn(None, "abcdefg") == "abcdefg"
    assert fn(None, "abcdefgh") == "abcdefg"
