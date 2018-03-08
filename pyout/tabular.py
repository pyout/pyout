"""Interface for styling tabular output.

This module defines the Tabular entry point.
"""

from __future__ import unicode_literals

from collections import Mapping, OrderedDict, Sequence
from contextlib import contextmanager
from functools import partial
import inspect
import multiprocessing
from multiprocessing.dummy import Pool

from blessings import Terminal

from pyout.field import TermProcessors
from pyout.common import RowNormalizer, StyleFields


class Tabular(object):
    """Interface for writing and updating styled terminal output.

    Parameters
    ----------
    columns : list of str or OrderedDict, optional
        Column names.  An OrderedDict can be used instead of a sequence to
        provide a map of short names to the displayed column names.

        If not given, the keys will be extracted from the first row of data
        that the object is called with, which is particularly useful if the row
        is an OrderedDict.  This argument must be given if this instance will
        not be called with a mapping.
    style : dict, optional
        Each top-level key should be a column name and the value should be a
        style dict that overrides the `default_style` class attribute.  See the
        "Examples" section below.
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

    The first field, "name", is taken as the unique ID.  The `style` argument
    is used to override the default width for the "status" field that is
    defined by the class attribute `default_style`.

    Write a row to stdout:

    >>> out({"name": "foo", "status": "OK"})

    Write another row, overriding the style:

    >>> out({"name": "bar", "status": "BAD"},
    ...     style={"status": {"color": "red", "bold": True}})
    """

    def __init__(self, columns=None, style=None, stream=None, force_styling=False):
        self.term = Terminal(stream=stream, force_styling=force_styling)

        self._rows = []
        self._columns = columns
        self._ids = None
        self._normalizer = None

        self._sfields = StyleFields(style, TermProcessors(self.term))

        if columns is not None:
            self._init_after_columns()

        self._pool = None
        self._lock = None

    def _init_after_columns(self):
        self._sfields.build(self._columns)
        self._normalizer = RowNormalizer(self._columns, self._sfields.style)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.wait()

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

        This should allow multiple threads or processes to write output
        reliably.  Code that modifies the `_rows` attribute should also do so
        within this context.
        """
        if self._lock:
            self._lock.acquire()
        try:
            yield
        finally:
            if self._lock:
                self._lock.release()

    def _write(self, content):
        self.term.stream.write(content)

    def _check_and_write(self, row, style, adopt=True,
                         repaint=True, no_write=False):
        """Main internal entry point for writing a row.

        Parameters
        ----------
        row : dict
           Data to write.
        style : dict or None
            Overriding style or None.
        adopt : bool, optional
            If true, overlay `style` on top of `self._style`.  Otherwise, treat
            `style` as a standalone style.
        repaint : bool, optional
            Whether to repaint if width check reports that previous widths are
            stale.
        no_write : bool, optional
            Do the check but don't write.  Instead, return the processor keys
            that can be used to call self._writerow directly.
        """
        repainted = False
        line, adjusted = self._sfields.render(row, style, adopt=adopt)
        if adjusted and repaint:
            self._repaint()
            repainted = True

        if no_write:
            return line, repainted
        self._write(line)

    def _maybe_write_header(self):
        if not self._sfields.has_header:
            return

        if isinstance(self._columns, OrderedDict):
            row = self._columns
        else:
            row = dict(zip(self._columns, self._columns))

        # Set repaint=False because we're at the header, so there
        # aren't any previous lines to update.
        self._check_and_write(row, self._sfields.style["header_"],
                              adopt=False, repaint=False)

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
                # Don't bother raising an exception if cols != 1
                # because it would be lost in the thread.
                tab.rewrite(id_vals, {cols[0]: result})

        if self._pool is None:
            self._pool = Pool()
        if self._lock is None:
            self._lock = multiprocessing.Lock()

        for cols, fn in callables:
            cb_func = partial(callback, self, cols)

            gen = None
            if inspect.isgeneratorfunction(fn):
                gen = fn()
            elif inspect.isgenerator(fn):
                gen = fn

            if gen:
                def callback_for_each():
                    for i in gen:
                        cb_func(i)
                self._pool.apply_async(callback_for_each)
            else:
                self._pool.apply_async(fn, callback=cb_func)

    def __call__(self, row, style=None):
        """Write styled `row` to the terminal.

        Parameters
        ----------
        row : mapping, sequence, or other
            If a mapping is given, the keys are the column names and values are
            the data to write.  For a sequence, the items represent the values
            and are taken to be in the same order as the constructor's
            `columns` argument.  Any other object type should have an attribute
            for each column specified via `columns`.

            Instead of a plain value, a column's value can be a tuple of the
            form (initial_value, producer).  If a producer is is a generator
            function or a generator object, each item produced replaces
            `initial_value`.  Otherwise, a producer should be a function that
            will be called with no arguments and that returns the value with
            which to replace `initial_value`.  For both generators and normal
            functions, the execution will happen asynchronously.

            Directly supplying a producer as the value rather than
            (initial_value, producer) is shorthand for ("", producer).

            The producer can return an update for multiple columns.  To do so,
            the keys of `row` should include a tuple with the column names and
            the produced value should be a tuple with the same order as the key
            or a mapping from column name to the updated value.

            Using the (initial_value, producer) form requires some additional
            steps.  The `ids` property should be set unless the first column
            happens to be a suitable id.  Also, to instruct the program to wait
            for the updated values, the instance calls should be followed by a
            call to the `wait` method or the instance should be used as a
            context manager.
        style : dict, optional
            Each top-level key should be a column name and the value should be
            a style dict that overrides the class instance style.
        """
        if self._columns is None:
            self._columns = self._infer_columns(row)
            self._init_after_columns()

        callables, row = self._normalizer(row)

        with self._write_lock():
            if not self._rows:
                self._maybe_write_header()
            self._check_and_write(row, style)
            self._rows.append(row)
        if callables:
            self._start_callables(row, callables)

    @staticmethod
    def _infer_columns(row):
        try:
            columns = list(row.keys())
        except AttributeError:
            raise ValueError("Can't infer columns from data")
        # Make sure we don't have any multi-column keys.
        flat = []
        for column in columns:
            if isinstance(column, tuple):
                flat.extend(column)
            else:
                flat.append(column)
        return flat

    def _repaint(self):
        if self._rows or self._sfields.has_header:
            self._move_to_firstrow()
            self.term.stream.write(self.term.clear_eol)
            self._maybe_write_header()
            for row in self._rows:
                self.term.stream.write(self.term.clear_eol)
                line, _ = self._sfields.render(row)
                self._write(line)

    def _move_to_firstrow(self):
        ntimes = len(self._rows) + self._sfields.has_header
        self.term.stream.write(self.term.move_up * ntimes)

    @contextmanager
    def _moveback(self, n):
        self.term.stream.write(self.term.move_up * n + self.term.clear_eol)
        try:
            yield
        finally:
            self.term.stream.write(self.term.move_down * (n - 1))
            self.term.stream.flush()

    # FIXME: This will break with stderr and when the output scrolls.  Maybe we
    # could check term height and repaint?
    def rewrite(self, ids, values, style=None):
        """Rewrite a row.

        Parameters
        ----------
        ids : dict or sequence
            The keys are the column names that in combination uniquely identify
            a row when matched for the values.

            If the id column names are set through the `ids` property, a
            sequence of values can be passed instead of a dict.
        values : dict
            The keys are the columns to be updated, and the values are the new
            values.
        style : dict
            A new style dictionary to use for the new row.  All unspecified
            style elements are taken from the instance's `style`.
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

            # Set no_write=True because there is no reason to go back
            # and rewrite row if we've already repainted.
            line, repainted = self._check_and_write(self._rows[idx], style,
                                                    no_write=True)
            if not repainted:
                with self._moveback(nback):
                    self._write(line)
