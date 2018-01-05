"""Terminal styling for tabular data.

TODO: Come up with a better one-line description.  Should emphasize
style declaration.
"""

__version__ = "0.1.0"
__all__ = ["Tabular"]

from collections import Mapping, OrderedDict, Sequence
from contextlib import contextmanager
from functools import partial
import multiprocessing
from multiprocessing.dummy import Pool

from blessings import Terminal

try:
    from jsonschema import validate
except ImportError:
    validate = lambda *_: None


### Schema definition

SCHEMA = {
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


def _schema_default(prop):
    return SCHEMA["properties"][prop]["default"]


### Helper classes and functions


class Field(object):
    """Format, process, and render tabular fields.

    A Field instance is a template for a string that is defined by its
    width, text alignment, and its "processors".  When a field is
    called with a value, it renders the value as a string with the
    specified width and text alignment.  Before this string is
    returned, it is passed through the chain of processors.  The
    rendered string is the result returned by the last processor.

    Parameters
    ----------
    width : int
    align : {'left', 'right', 'center'}

    Attributes
    ----------
    width : int
    align : str
    processors : dict
        Each key maps to a list of processors.  The keys "core" and
        "default" must always be present.  When an instance object is
        called, the rendered result is always sent through the "core"
        processors.  It will then be sent through the "default"
        processors unless another key is provided as the optional
        `which` argument.

        A processor should take two positional arguments, the value
        that is being rendered and the current result.  Its return
        value will be passed to the next processor as the current
        result.
    """

    _align_values = {"left": "<", "right": ">", "center": "^"}

    def __init__(self, width=10, align="left"):
        self._width = width
        self._align = align
        self._fmt = self._build_format()

        self.processors = {"core": [], "default": []}

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        self._fmt = self._build_format()

    @property
    def align(self):
        return self._align

    @align.setter
    def align(self, value):
        self._align = value
        self._fmt = self._build_format()

    def _build_format(self):
        align = self._align_values[self.align]
        return "".join(["{:", align, str(self.width), "}"])

    def __call__(self, value, which="default"):
        """Render `value` by feeding it through the processors.

        Parameters
        ----------
        value : str
        which : str, optional
            A key for the `processors` attribute that indicates the
            list of processors to use in addition to the "core" list.
        """
        result = self._fmt.format(value)
        for fn in self.processors["core"] + self.processors[which]:
            result = fn(value, result)
        return result


class StyleProcessors(object):
    """A base class for generating Field.processors for styled output.

    Attributes
    ----------
    style_keys : list of tuples
        Each pair consists of a style attribute (e.g., "bold") and the
        expected type.
    """

    style_keys = [("bold", bool),
                  ("underline", bool),
                  ("color", str)]

    def translate(self, name):
        """Translate a style key for a given output type.

        Parameters
        ----------
        name : str
            A style key (e.g., "bold").

        Returns
        -------
        An output-specific translation of `name`.
        """
        raise NotImplementedError

    @staticmethod
    def truncate(length, marker=True):
        """Return a processor that truncates the result to `length`.

        Note: You probably want to place this function at the
        beginning of the processor list so that the truncation is
        based on the length of the original value.

        Parameters
        ----------
        length : int
        marker : str or bool
            Indicate truncation with this string.  If True, indicate
            truncation by replacing the last three characters of a
            truncated string with '...'.  If False, no truncation
            marker is added to a truncated string.

        Returns
        -------
        A function.
        """
        if marker is True:
            marker = "..."

        ## TODO: Add an option to center the truncation marker?
        def truncate_fn(_, result):
            if len(result) <= length:
                return result
            if marker:
                marker_beg = max(length - len(marker), 0)
                if result[marker_beg:].strip():
                    if marker_beg == 0:
                        return marker[:length]
                    return result[:marker_beg] + marker
            return result[:length]
        return truncate_fn

    def by_key(self, key):
        """Return a processor for the style given by `key`.

        Parameters
        ----------
        key : str
            A style key to be translated.

        Returns
        -------
        A function.
        """
        def by_key_fn(_, result):
            return self.translate(key) + result
        return by_key_fn

    def by_lookup(self, mapping, key=None):
        """Return a processor that extracts the style from `mapping`.

        Parameters
        ----------
        mapping : mapping
            A map from the field value to a style key, or, if `key` is
            given, a map from the field value to a value that
            indicates whether the processor should style its result.
        key : str, optional
            A style key to be translated.  If not given, the value
            from `mapping` is used.

        Returns
        -------
        A function.
        """
        def by_lookup_fn(value, result):
            try:
                lookup_value = mapping[value]
            except KeyError:
                return result

            if not lookup_value:
                return result
            return self.translate(key or lookup_value) + result
        return by_lookup_fn

    def by_interval_lookup(self, intervals, key=None):
        """Return a processor that extracts the style from `intervals`.

        Parameters
        ----------
        intervals : sequence of tuples
            Each tuple should have the form `(start, end, key)`, where
            start is the start of the interval (inclusive) , end is
            the end of the interval, and key is a style key.
        key : str, optional
            A style key to be translated.  If not given, the value
            from `mapping` is used.

        Returns
        -------
        A function.
        """
        def by_interval_lookup_fn(value, result):
            value = float(value)
            for start, end, lookup_value in intervals:
                if start is None:
                    start = float("-inf")
                elif end is None:
                    end = float("inf")

                if start <= value < end:
                    if not lookup_value:
                        return result
                    return self.translate(key or lookup_value) + result
            return result
        return by_interval_lookup_fn

    @staticmethod
    def value_type(value):
        """Classify `value` of bold, color, and underline keys.

        Parameters
        ----------
        value : style value

        Returns
        -------
        str, {"simple", "label", "interval"}
        """
        try:
            keys = list(value.keys())
        except AttributeError:
            return "simple"
        if keys in [["label"], ["interval"]]:
            return keys[0]
        raise ValueError("Type of `value` could not be determined")

    def from_style(self, column_style):
        """Yield processors based on `column_style`.

        Parameters
        ----------
        column_style : dict
            A style where the top-level keys correspond to style
            attributes such as "bold" or "color".

        Returns
        -------
        A generator object.
        """
        for key, key_type in self.style_keys:
            if key not in column_style:
                continue

            vtype = self.value_type(column_style[key])
            attr_key = key if key_type is bool else None

            if vtype == "simple":
                if key_type is bool:
                    if column_style[key] is True:
                        yield self.by_key(key)
                elif key_type is str:
                    yield self.by_key(column_style[key])
            elif vtype == "label":
                yield self.by_lookup(column_style[key][vtype], attr_key)
            elif vtype == "interval":
                yield self.by_interval_lookup(column_style[key][vtype],
                                              attr_key)


class TermProcessors(StyleProcessors):
    """Generate Field.processors for styled Terminal output.

    Parameters
    ----------
    term : blessings.Terminal
    """

    def __init__(self, term):
        self.term = term

    def translate(self, name):
        """Translate a style key into a Terminal code.

        Parameters
        ----------
        name : str
            A style key (e.g., "bold").

        Returns
        -------
        An output-specific translation of `name` (e.g., "\x1b[1m").
        """
        return str(getattr(self.term, name))

    def _maybe_reset(self):
        def maybe_reset_fn(_, result):
            if "\x1b" in result:
                return result + self.term.normal
            return result
        return maybe_reset_fn

    def from_style(self, column_style):
        """Call StyleProcessors.from_style, adding a Terminal-specific reset.
        """
        for proc in super(TermProcessors, self).from_style(column_style):
            yield proc
        yield self._maybe_reset()


def _adopt(style, new_style):
    if new_style is None:
        return style

    combined = {}
    for key, value in style.items():
        if isinstance(value, Mapping):
            combined[key] = dict(value, **new_style.get(key, {}))
        else:
            combined[key] = new_style.get(key, value)
    return combined


def _safe_get(mapping, key, default=None):
    try:
        return mapping.get(key, default)
    except AttributeError:
        return default


class RewritePrevious(Exception):
    """Signal that the previous output needs to be updated.
    """
    pass


### Tabular interface


class Tabular(object):
    """Interface for writing and updating styled terminal output.

    Parameters
    ----------
    columns : list of str or OrderedDict, optional
        Column names.  An OrderedDict can be used instead of a
        sequence to provide a map of short names to the displayed
        column names.

        If not given, the keys will be extracted from the first row of
        data that the object is called with, which is particularly
        useful if the row is an OrderedDict.  This argument must be
        given if this instance will not be called with a mapping.
    style : dict, optional
        Each top-level key should be a column name and the value
        should be a style dict that overrides the `default_style`
        class attribute.  See the "Examples" section below.
    stream : file object, optional
        Defaults to standard output.

    force_styling : bool or None
        Passed to blessings.Terminal.

    Attributes
    ----------
    term : blessings.Terminal instance

    Examples
    --------

    Create a `Tabular` instance for two output fields, "name" and
    "status".

    >>> out = Tabular(["name", "status"], style={"status": {"width": 5}})

    The first field, "name", is taken as the unique ID.  The `style`
    argument is used to override the default width for the "status"
    field that is defined by the class attribute `default_style`.

    Write a row to stdout:

    >>> out({"name": "foo", "status": "OK"})

    Write another row, overriding the style:

    >>> out({"name": "bar", "status": "BAD"},
    ...     style={"status": {"color": "red", "bold": True}})
    """

    _header_attributes = {"align", "width"}

    def __init__(self, columns=None, style=None, stream=None, force_styling=False):
        self.term = Terminal(stream=stream, force_styling=force_styling)
        self._tproc = TermProcessors(self.term)

        self._rows = []
        self._columns = columns
        self._ids = None
        self._fields = None
        self._transform_method = None

        self._init_style = style
        self._style = None

        self._autowidth_columns = {}

        if columns is not None:
            self._setup_style()
            self._setup_fields()

        self._pool = None
        self._lock = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self._pool is None:
            return
        self._pool.close()
        self._pool.join()

    def _setup_style(self):
        default = dict(_schema_default("default_"),
                       **_safe_get(self._init_style, "default_", {}))
        self._style = _adopt({c: default for c in self._columns},
                             self._init_style)

        hstyle = None
        if self._init_style is not None and "header_" in self._init_style:
            hstyle = {}
            for col in self._columns:
                cstyle = {k: v for k, v in self._style[col].items()
                          if k in self._header_attributes}
                hstyle[col] = dict(cstyle, **self._init_style["header_"])

        ## Store special keys in _style so that they can be validated.
        self._style["default_"] = default
        self._style["header_"] = hstyle
        self._style["separator_"] = _safe_get(self._init_style, "separator_",
                                              _schema_default("separator_"))

        validate(self._style, SCHEMA)

    def _setup_fields(self):
        self._fields = {}
        for column in self._columns:
            cstyle = self._style[column]

            procs = []
            style_width = cstyle["width"]
            is_auto = style_width == "auto" or _safe_get(style_width, "auto")

            if is_auto:
                width = _safe_get(style_width, "min", 1)
                wmax = _safe_get(style_width, "max")

                self._autowidth_columns[column] = {"max": wmax}

                if wmax is not None:
                    marker = _safe_get(style_width, "marker", True)
                    procs = [self._tproc.truncate(wmax, marker)]
            elif is_auto is False:
                raise ValueError("No 'width' specified")
            else:
                width = style_width
                procs = [self._tproc.truncate(width)]

            field = Field(width=width, align=cstyle["align"])
            field.processors["core"] = procs
            field.processors["default"] = list(self._tproc.from_style(cstyle))

            self._fields[column] = field

    @property
    def ids(self):
        if self._ids is None:
            if self._columns:
                return [self._columns[0]]
        else:
            return self._ids

    @ids.setter
    def ids(self, columns):
        self._ids = columns

    @staticmethod
    def _identity(row):
        return row

    def _seq_to_dict(self, row):
        return dict(zip(self._columns, row))

    def _attrs_to_dict(self, row):
        return {c: getattr(row, c) for c in self._columns}

    def _choose_transform_method(self, row):
        if isinstance(row, Mapping):
            return self._identity
        if isinstance(row, Sequence):
            return self._seq_to_dict
        return self._attrs_to_dict

    def _set_widths(self, row):
        """Update auto-width Fields based on `row`.

        Parameters
        ----------
        row : dict

        Raises
        ------
        RewritePrevious to signal that previously written rows, if
        any, may be stale.
        """
        rewrite = False
        for column in self._columns:
            if column in self._autowidth_columns:
                value_width = len(str(row[column]))
                wmax = self._autowidth_columns[column]["max"]
                if value_width > self._fields[column].width:
                    if wmax is None or self._fields[column].width < wmax:
                        rewrite = True
                    self._fields[column].width = value_width
        if rewrite:
            raise RewritePrevious

    @contextmanager
    def _write_lock(self):
        """Acquire and release the lock around output calls.

        This should allow multiple threads or processes to write
        output reliably.  Code that modifies the `_rows` attribute
        should also do so within this context.
        """
        lock = self._lock is not None
        if lock:
            self._lock.acquire()
        try:
            yield
        finally:
            if lock:
                self._lock.release()

    def _writerow(self, row, style=None, adopt=True):
        fields = self._fields

        if style is not None:
            validate(style, SCHEMA)

            rowstyle = _adopt(self._style, style) if adopt else style
            for column in self._columns:
                fields[column].processors["row"] = list(
                    self._tproc.from_style(rowstyle[column]))
            proc_key = "row"
        else:
            proc_key = "default"

        proc_fields = [fields[c](row[c], proc_key) for c in self._columns]
        self.term.stream.write(
            self._style["separator_"].join(proc_fields) + "\n")

    def _maybe_write_header(self):
        if self._style["header_"] is None:
            return

        transform = False

        if isinstance(self._columns, OrderedDict):
            row = self._columns
        elif self._transform_method == self._seq_to_dict:
            row = self._transform_method(self._columns)
        else:
            row = dict(zip(self._columns, self._columns))

        try:
            self._set_widths(row)
        except RewritePrevious:
            ## We're at the header, so there aren't any previous
            ## lines to update.
            pass
        self._writerow(row, style=self._style["header_"], adopt=False)

    def _strip_callables(self, row):
        """Replace (initial_value, callable) form in `row` with inital value.

        Returns
        -------
        list of (columns, callable)
        """
        callables = []
        to_delete = []
        to_add = []
        for columns, value in row.items():
            try:
                initial, fn = value
            except (ValueError, TypeError):
                continue
            else:
                if callable(fn):
                    if not isinstance(columns, tuple):
                        columns = columns,
                    else:
                        to_delete.append(columns)
                    for column in columns:
                        to_add.append((column, initial))
                    callables.append((columns, fn))

        for column, value in to_add:
            row[column] = value
        for multi_columns in to_delete:
            del row[multi_columns]

        return callables

    def _start_callables(self, row, callables):
        """Start running `callables` asynchronously.
        """
        id_vals = [row[c] for c in self.ids]
        def callback(tab, cols, result):
            if isinstance(result, Mapping):
                tab.rewrite(id_vals, result)
            elif isinstance(result, tuple):
                tab.rewrite(id_vals, dict(zip(cols, result)))
            else:
                if len(cols) != 1:
                    ValueError("Expected only one column")
                tab.rewrite(id_vals, {cols[0]: result})

        if self._pool is None:
            self._pool = Pool()
        if self._lock is None:
            self._lock = multiprocessing.Lock()

        for cols, fn in callables:
            self._pool.apply_async(fn,
                                   callback=partial(callback, self, cols))

    def __call__(self, row, style=None):
        """Write styled `row` to the terminal.

        Parameters
        ----------
        row : mapping, sequence, or other
            If a mapping is given, the keys are the column names and
            values are the data to write.  For a sequence, the items
            represent the values and are taken to be in the same order
            as the constructor's `columns` argument.  Any other object
            type should have an attribute for each column in specified
            via `columns`.

            Instead of a plain value, a column's value can be a tuple
            of the form (initial_value, callable).  The callable will
            be called asynchronously with no arguments and should
            return the value with which to replace `initial_value`.

            Using callable values requires some additional steps.  The
            `ids` property should be set unless the first column
            happens to be a suitable id.  The instance should also be
            used as a context manager so that the program waits at the
            end of the block for the return values.
        style : dict, optional
            Each top-level key should be a column name and the value
            should be a style dict that overrides the class instance
            style.
        """
        if self._columns is None:
            self._columns = self._infer_columns(row)
            self._setup_style()
            self._setup_fields()

        if self._transform_method is None:
            self._transform_method = self._choose_transform_method(row)
        row = self._transform_method(row)
        callables = self._strip_callables(row)

        with self._write_lock():
            if not self._rows:
                self._maybe_write_header()

            try:
                self._set_widths(row)
            except RewritePrevious:
                self._repaint()
            self._writerow(row, style=style)
            self._rows.append(row)
        if callables:
            self._start_callables(row, callables)

    @staticmethod
    def _infer_columns(row):
        try:
            columns = list(row.keys())
        except AttributeError:
            raise ValueError("Can't infer columns from data")
        ## Make sure we don't have any multi-column keys.
        flat = []
        for column in columns:
            if isinstance(column, tuple):
                for c in column:
                    flat.append(c)
            else:
                flat.append(column)
        return flat

    def _repaint(self):
        if self._rows or self._style["header_"] is not None:
            self._move_to_firstrow()
            self.term.stream.write(self.term.clear_eol)
            self._maybe_write_header()
            for row in self._rows:
                self.term.stream.write(self.term.clear_eol)
                self._writerow(row)

    def _move_to_firstrow(self):
        ntimes = len(self._rows) + (self._style["header_"] is not None)
        self.term.stream.write(self.term.move_up * ntimes)

    @contextmanager
    def _moveback(self, n):
        self.term.stream.write(self.term.move_up * n + self.term.clear_eol)
        try:
            yield
        finally:
            self.term.stream.write(self.term.move_down * (n - 1))
            self.term.stream.flush()

    ## FIXME: This will break with stderr and when the output scrolls.
    ## Maybe we could check term height and repaint?
    def rewrite(self, ids, values, style=None):
        """Rewrite a row.

        Parameters
        ----------
        ids : dict or sequence
            The keys are the column names that in combination uniquely
            identify a row when matched for the values.

            If the id column names are set through the `ids` property,
            a sequence of values can be passed instead of a dict.
        values : dict
            The keys are that columns to be updated, and the values
            are the new values.
        style : dict
            A new style dictionary to use for the new row.  All
            unspecified style elements are taken from the instance's
            `style`.
        """
        if isinstance(ids, Sequence):
            ids = dict(zip(self.ids, ids))

        with self._write_lock():
            nback = None
            for rev_idx, row in enumerate(reversed(self._rows), 1):
                if all(row[k] == v for k, v in ids.items()):
                    nback = rev_idx
                    break
            if nback is None:
                raise ValueError("Could not find row for {}".format(ids))

            idx = len(self._rows) - nback
            self._rows[idx].update(values)

            try:
                self._set_widths(self._rows[idx])
            except RewritePrevious:
                self._repaint()
            else:
                with self._moveback(nback):
                    self._writerow(self._rows[idx], style)
