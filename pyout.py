"""Terminal styling for tabular data.

TODO: Come up with a better one-line description.  Should emphasize
style declaration.
"""

__version__ = "0.1.0"
__all__ = ["Tabular"]

from collections import OrderedDict
from contextlib import contextmanager
from blessings import Terminal


def _adopt(style, new_style):
    if new_style is None:
        return style
    return {key: dict(style[key], **new_style.get(key, {})) for key in style}


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
        given if this instance will be called with a sequence rather
        than a dictionary.
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

    # TODO: Support things like auto-width, value-based coloring, etc.
    default_style = {"align": "<",
                     "width": 10}

    _header_attributes = {"align", "width"}

    def __init__(self, columns=None, style=None, stream=None, force_styling=False):
        self.term = Terminal(stream=stream, force_styling=force_styling)

        self._rows = []
        self._columns = columns

        self._init_style = style
        self._style = None
        self._header_style = None
        if columns is not None:
            self._setup_style()
        self._format = None

    def _setup_style(self):
        self._style = _adopt({c: self.default_style for c in self._columns},
                             self._init_style)

        if self._init_style is not None and "header_" in self._init_style:
            self._header_style = {}
            for col in self._columns:
                cstyle = {k: v for k, v in self._style[col].items()
                          if k in self._header_attributes}
                self._header_style[col] = dict(cstyle,
                                               **self._init_style["header_"])

    def _build_format(self, style):
        fields = []
        for column in self._columns:
            cstyle = style[column]

            attrs = (self._map_to_blessings(k, v) for k, v in cstyle.items())
            attrs = list(filter(None, attrs))

            field = "{{{}:{align}{width}}}".format(column, **cstyle)
            pre = "".join(getattr(self.term, a) for a in attrs)
            post = self.term.normal if pre else ""

            fields.append(pre + field + post)
        return " ".join(fields) + "\n"

    def _map_to_blessings(self, key, value):
        """Convert a key-value pair into a `blessings.Terminal` attribute.

        Parameters
        ----------
        key, value : str
            Attribute key (e.g., "color") and value (e.g., "green")

        Returns
        -------
        str (attribute value) or None
        """
        if key in ["bold", "underline"]:
            if value:
                return key
        elif key == "color":
            return value

    _preformat_method = lambda self, x: x

    def _seq_to_dict(self, row):
        return dict(zip(self._columns, row))

    def _writerow(self, row, style=None, adopt=True):
        if self._format is not None and style is None:
            fmt = self._format
        else:
            if adopt:
                fmt = self._build_format(_adopt(self._style, style))
            else:
                fmt = self._build_format(style)

        try:
            self.term.stream.write(fmt.format(**self._preformat_method(row)))
        except TypeError:
            if self._preformat_method == self._seq_to_dict:
                raise
            self._preformat_method = self._seq_to_dict
            self._writerow(row, style)

    def _maybe_write_header(self):
        if self._header_style is not None:
            if self._preformat_method == self._seq_to_dict:
                row = self._columns
            else:
                if isinstance(self._columns, OrderedDict):
                    row = self._columns
                else:
                    row = dict(zip(self._columns, self._columns))
            self._writerow(row, style=self._header_style, adopt=False)

    def __call__(self, row, style=None):
        """Write styled `row` to the terminal.

        Parameters
        ----------
        row : dict or sequence
            A dictionary where keys are the column names and values
            are the data to write.  Otherwise, row is treated as a
            sequence that follows the same order as the constructor's
            `columns` argument.
        style : dict, optional
            Each top-level key should be a column name and the value
            should be a style dict that overrides the class instance
            style.
        """
        if self._columns is None:
            self._columns = self._infer_columns(row)
            self._setup_style()

        if not self._rows:
            self._maybe_write_header()
        self._rows.append(row)
        self._writerow(row, style=style)

    def _infer_columns(self, row):
        try:
            return list(row.keys())
        except AttributeError:
            raise ValueError("Can't infer columns from data")

    def _repaint(self):
        ## TODO: I don't think this is a good approach.  Destroys any
        ## scroll back.
        self.term.stream.write(self.term.clear)
        self._maybe_write_header()
        for row in self._rows:
            self._writerow(row)
        self.term.stream.flush()

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
    def rewrite(self, ids, column, new_value, style=None):
        """Rewrite a row.

        Parameters
        ----------
        ids : dict
            The keys are the column names that in combination uniquely
            identify a row when matched for the values.
        column : str
            The name of the column whose value should be updated to
            `new_value`.
        new_value : str
        style : dict
            A new style dictionary to use for the new row.  All
            unspecified style elements are taken from the instance's
            `style`.
        """
        nback = None
        for rev_idx, row in enumerate(reversed(self._rows), 1):
            if all(row[k] == v for k, v in ids.items()):
                nback = rev_idx
                break
        if nback is None:
            raise ValueError("Could not find row for {}".format(ids))

        idx = len(self._rows) - nback
        self._rows[idx][column] = new_value

        with self._moveback(nback):
            self._writerow(self._rows[idx], style)
