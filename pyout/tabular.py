"""Interface for styling tabular output.

This module defines the Tabular entry point.
"""

from __future__ import unicode_literals

from collections import Mapping, OrderedDict
from contextlib import contextmanager
from functools import partial
import inspect
import multiprocessing
from multiprocessing.dummy import Pool

from blessings import Terminal

from pyout.field import TermProcessors
from pyout.common import ContentWithSummary, RowNormalizer, StyleFields


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

        self._columns = columns
        self._ids = None

        self._content = ContentWithSummary(
            StyleFields(style, TermProcessors(self.term)))
        self._last_content_len = 0
        self._last_summary_len = 0
        self._normalizer = None

        self._pool = None
        self._lock = None

    def _init_prewrite(self):
        self._content.init_columns(self._columns, self.ids)
        self._normalizer = RowNormalizer(self._columns,
                                         self._content.fields.style)

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
                if isinstance(self._columns, OrderedDict):
                    return [list(self._columns.keys())[0]]
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
        reliably.  Code that modifies the `_content` attribute should also do
        so within this context.
        """
        if self._lock:
            self._lock.acquire()
        try:
            yield
        finally:
            if self._lock:
                self._lock.release()

    def _write(self, row, style=None):
        with self._write_lock():
            if self._last_summary_len:
                # Clear the summary because 1) it has very likely changed, 2)
                # it makes the counting for row updates simpler, 3) and it is
                # possible for the summary lines to shrink.
                #
                # FIXME: This, like other line counting-based modifications in
                # pyout, will fail if there is any line wrapping.  We need to
                # detect the terminal width and somehow handle this.
                self._clear_last_summary()
            content, status, summary = self._content.update(row, style)
            if isinstance(status, int):
                with self._moveback(self._last_content_len - status):
                    self.term.stream.write(content)
            else:
                if status == "repaint":
                    self._move_to_firstrow()
                self.term.stream.write(content)

            if summary is not None:
                self.term.stream.write(summary)
                self._last_summary_len = len(summary.splitlines())
            self._last_content_len = len(self._content)

    def _start_callables(self, row, callables):
        """Start running `callables` asynchronously.
        """
        id_vals = {c: row[c] for c in self.ids}

        def callback(tab, cols, result):
            if isinstance(result, Mapping):
                pass
            elif isinstance(result, tuple):
                result = dict(zip(cols, result))
            elif len(cols) == 1:
                # Don't bother raising an exception if cols != 1
                # because it would be lost in the thread.
                result = {cols[0]: result}
            result.update(id_vals)
            tab._write(result)

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
        if self._normalizer is None:
            self._init_prewrite()

        callables, row = self._normalizer(row)
        self._write(row, style)
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

    def _move_to_firstrow(self):
        self.term.stream.write(self.term.move_up * self._last_content_len)

    @contextmanager
    def _moveback(self, n):
        self.term.stream.write(self.term.move_up * n + self.term.clear_eol)
        try:
            yield
        finally:
            self.term.stream.write(self.term.move_down * (n - 1))
            self.term.stream.flush()

    def _clear_last_summary(self):
        self.term.stream.write(
            self.term.move_up * self._last_summary_len + self.term.clear_eos)
        self.term.stream.flush()
