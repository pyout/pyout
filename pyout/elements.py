from collections import Mapping

schema = {
    "definitions": {
        ## Styles
        "align": {
            "description": "Alignment of text",
            "type": "string",
            "enum": ["left", "right", "center"],
            "default": "left",
            "scope": "table"},
        "bold": {
            "description": "Whether text is bold",
            "oneOf": [{"type": "boolean"},
                      {"$ref": "#/definitions/label"},
                      {"$ref": "#/definitions/interval"}],
            "default": False,
            "scope": "field"},
        "color": {
            "description": "Foreground color of text",
            "oneOf": [{"type": "string",
                       "enum": ["black", "red", "green", "yellow",
                                "blue", "magenta", "cyan", "white"]},
                      {"$ref": "#/definitions/label"},
                      {"$ref": "#/definitions/interval"}],
            "default": "black",
            "scope": "field"},
        "underline": {
            "description": "Whether text is underlined",
            "oneOf": [{"type": "boolean"},
                      {"$ref": "#/definitions/label"},
                      {"$ref": "#/definitions/interval"}],
            "default": False,
            "scope": "field"},
        "width": {
            "description": "Width of field",
            "oneOf": [{"type": "integer"},
                      {"type": "string",
                       "enum": ["auto"]},
                      {"type": "object",
                       "properties": {
                           "auto": {"type": "boolean"},
                           "max": {"type": ["integer", "null"]},
                           "min": {"type": ["integer", "null"]}}}],
            "default": "auto",
            "scope": "table"},
        "styles": {
            "type": "object",
            "properties": {"align": {"$ref": "#/definitions/align"},
                           "bold": {"$ref": "#/definitions/bold"},
                           "color": {"$ref": "#/definitions/color"},
                           "underline": {"$ref": "#/definitions/underline"},
                           "width": {"$ref": "#/definitions/width"}},
            "additionalProperties": False},
        ## Mapping types
        "interval": {
            "description": "Map a value within an interval to a style",
            "type": "object",
            "properties": {"interval":
                           {"type": "array",
                            "items": [
                                {"type": "array",
                                 "items": [{"type": ["number", "null"]},
                                           {"type": ["number", "null"]},
                                           {"type": ["string", "boolean"]}],
                                 "additionalItems": False}]}},
            "additionalProperties": False},
        "label": {
            "description": "Map a value to a style",
            "type": "object",
            "properties": {"label": {"type": "object"}},
            "additionalProperties": False}
    },
    "type": "object",
    "properties": {
        "default_": {
            "description": "Default style of columns",
            "oneOf": [{"$ref": "#/definitions/styles"},
                      {"type": "null"}],
            "default": {"align": "left",
                        "width": "auto"},
            "scope": "table"},
        "header_": {
            "description": "Attributes for the header row",
            "oneOf": [{"type": "object",
                       "properties":
                       {"color": {"$ref": "#/definitions/color"},
                        "bold": {"$ref": "#/definitions/bold"},
                        "underline": {"$ref": "#/definitions/underline"}}},
                      {"type": "null"}],
            "default": None,
            "scope": "table"},
        "separator_": {
            "description": "Separator used between fields",
            "type": "string",
            "default": " ",
            "scope": "table"}
    },
    ## All other keys are column names.
    "additionalProperties": {"$ref": "#/definitions/styles"}
}


def default(prop):
    return schema["properties"][prop]["default"]


try:
    from jsonschema import validate
except ImportError:
    validate = lambda *_: None


def adopt(style, new_style):
    if new_style is None:
        return style

    combined = {}
    for key, value in style.items():
        if isinstance(value, Mapping):
            combined[key] = dict(value, **new_style.get(key, {}))
        else:
            combined[key] = new_style.get(key, value)
    return combined
