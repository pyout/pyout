import pytest

from pyout.elements import adopt
from pyout.elements import StyleValidationError
from pyout.elements import validate
from pyout.elements import value_type


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
    with pytest.raises(StyleValidationError):
        validate("not ok")


def test_validate_ok():
    validate({})
    validate({"header_": {"colname": {"bold": True}}})


def test_value_type():
    assert value_type(True) == "simple"
    assert value_type("red") == "simple"
    assert value_type({"lookup": {"BAD": "red"}}) == "lookup"

    interval = {"interval": [(0, 50, "red"), (50, 80, "yellow")]}
    assert value_type(interval) == "interval"

    with pytest.raises(ValueError):
        value_type({"unknown": 1})
