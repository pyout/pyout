from __future__ import unicode_literals

import pytest

from pyout.elements import adopt
from pyout.elements import StyleValidationError
from pyout.elements import validate


def test_adopt_noop():
    default_value = {"align": "<",
                     "width": 10,
                     "attrs": []}

    style = {"name": default_value,
             "path": default_value,
             "status": default_value}

    newstyle = adopt(style, None)
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

    newstyle = adopt(style, {"path": {"width": 99},
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


def test_validate_error():
    pytest.importorskip("jsonschema")
    with pytest.raises(StyleValidationError):
        validate("not ok")


def test_validate_ok():
    validate({})
    validate({"header_": {"colname": {"bold": True}}})
