"""Interface for styling tabular output.

This module defines the Tabular entry point.
"""

from collections import Mapping, OrderedDict, Sequence
from contextlib import contextmanager
from functools import partial
import multiprocessing
from multiprocessing.dummy import Pool

from blessings import Terminal

from pyout import elements
from pyout.field import Field, StyleProcessors


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


def _safe_get(mapping, key, default=None):
    try:
        return mapping.get(key, default)
    except AttributeError:
        return default


class RewritePrevious(Exception):
    """Signal that the previous output needs to be updated.
    """
    pass


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
        self.wait()

    def _setup_style(self):
        default = dict(elements.default("default_"),
                       **_safe_get(self._init_style, "default_", {}))
        self._style = elements.adopt({c: default for c in self._columns},
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
                                              elements.default("separator_"))

        elements.validate(self._style)

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
        """A list of unique IDs used to identify a row.

        If not explicitly set, it defaults to the first column name.
        """
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

    def wait(self):
        """Wait for asynchronous calls to return.
        """
        if self._pool is None:
            return
        self._pool.close()
        self._pool.join()

    @contextmanager
    def _write_lock(self):
        """Acquire and release the lock around output calls.

        This should allow multiple threads or processes to write
        output reliably.  Code that modifies the `_rows` attribute
        should also do so within this context.
        """
        if self._lock:
            self._lock.acquire()
        try:
            yield
        finally:
            if self._lock:
                self._lock.release()

    def _writerow(self, row, style=None, adopt=True):
        fields = self._fields

        if style is not None:
            elements.validate(style)

            rowstyle = elements.adopt(self._style, style) if adopt else style
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

    @staticmethod
    def _strip_callables(row):
        """Replace (initial_value, callable) form in `row` with initial value.

        Returns
        -------
        list of (column, callable)
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
            elif len(cols) == 1:
                ## Don't bother raising an exception if cols != 1
                ## because it would be lost in the thread.
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