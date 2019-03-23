"""Core pyout interface definitions.
"""

from __future__ import unicode_literals

import abc
from collections import Mapping
from collections import OrderedDict
from contextlib import contextmanager
from functools import partial
import inspect
from logging import getLogger
import multiprocessing
from multiprocessing.dummy import Pool
import sys

import six

from pyout.common import ContentWithSummary
from pyout.common import RowNormalizer
from pyout.common import StyleFields
from pyout.field import PlainProcessors

lgr = getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Stream(object):
    """Output stream interface used by Writer.

    Parameters
    ----------
    stream : stream, optional
        Stream to write output to.  Defaults to sys.stdout.
    interactive : boolean, optional
        Whether this stream is interactive.  If not specified, it will be set
        to the return value of `stream.isatty()`.

    Attributes
    ----------
    interactive : bool
    supports_updates : boolean
        If true, the writer supports updating previous lines.
    """

    supports_updates = True

    def __init__(self, stream=None, interactive=None):
        self.stream = stream or sys.stdout
        if interactive is None:
            self.interactive = self.stream.isatty()
        else:
            self.interactive = interactive
        self.supports_updates = self.interactive

    @abc.abstractproperty
    def width(self):
        """Maximum line width.
        """
    @abc.abstractproperty
    def height(self):
        """Maximum number of rows that are visible."""

    @abc.abstractmethod
    def write(self, text):
        """Write `text`.
        """

    @abc.abstractmethod
    def clear_last_lines(self, n):
        """Clear previous N lines.
        """

    @abc.abstractmethod
    def overwrite_line(self, n, text):
        """Go to the Nth previous line and overwrite it with `text`
        """

    @abc.abstractmethod
    def move_to(self, n):
        """Move the Nth previous line.
        """


class Writer(object):
    """Base class implementing the core handling logic of pyout output.

    To define a writer, a subclass should inherit Writer and define __init__ to
     call Writer.__init__ and then the _init method.
    """
    def __init__(self, columns=None, style=None, stream=None,
                 interactive=None):
        self._columns = columns
        self._ids = None

        self._last_content_len = 0
        self._last_summary = None
        self._normalizer = None

        self._pool = None
        self._lock = None

        self._mode = None
        self._write_fn = None

        self._stream = None
        self._content = None

    def _init(self, style, streamer, processors=None):
        """Do writer-specific setup.

        Parameters
        ----------
        style : dict
            Style, as passed to __init__.
        streamer : interface.Stream
            A stream interface that takes __init__'s `stream` and `interactive`
            arguments into account.
        processors : field.StyleProcessors, optional
            A writer-specific processors instance.  Defaults to
            field.PlainProcessors().
        """
        self._stream = streamer
        if streamer.interactive:
            if streamer.supports_updates:
                self.mode = "update"
            else:
                self.mode = "incremental"
        else:
            self.mode = "final"

        if style and "width_" not in style and self._stream.width:
            style["width_"] = self._stream.width
        self._content = ContentWithSummary(
            StyleFields(style, processors or PlainProcessors()))

    def _init_prewrite(self):
        self._content.init_columns(self._columns, self.ids)
        self._normalizer = RowNormalizer(self._columns,
                                         self._content.fields.style)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.wait()
        if self.mode == "final":
            self._stream.write(six.text_type(self._content))
        if self.mode != "update" and self._last_summary is not None:
            self._stream.write(six.text_type(self._last_summary))

    @property
    def mode(self):
        """Mode of display.

        * update (default): Go back and update the fields.  This includes
          resizing the automated widths.

        * incremental: Don't go back to update anything.

        * final: finalized representation appropriate for redirecting to file
        """
        return self._mode

    @mode.setter
    def mode(self, value):
        valid = {"update", "incremental", "final"}
        if value not in valid:
            raise ValueError("{!r} is not a valid mode: {!r}"
                             .format(value, valid))
        if self._content:
            raise ValueError("Must set mode before output has been written")

        lgr.debug("Setting write mode to %r", value)
        self._mode = value
        if value == "incremental":
            self._write_fn = self._write_incremental
        elif value == "final":
            self._write_fn = self._write_final
        else:
            if self._stream.supports_updates and self._stream.interactive:
                self._write_fn = self._write_update
            else:
                raise ValueError("Stream {} does not support updates"
                                 .format(self._stream))

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
            lgr.debug("Acquiring write lock")
            self._lock.acquire()
        try:
            yield
        finally:
            if self._lock:
                lgr.debug("Releasing write lock")
                self._lock.release()

    def _write(self, row, style=None):
        with self._write_lock():
            self._write_fn(row, style)

    def _write_update(self, row, style=None):
        if self._last_summary:
            last_summary_len = len(self._last_summary.splitlines())
            # Clear the summary because 1) it has very likely changed, 2)
            # it makes the counting for row updates simpler, 3) and it is
            # possible for the summary lines to shrink.
            lgr.debug("Clearing summary")
            self._stream.clear_last_lines(last_summary_len)
        else:
            last_summary_len = 0

        content, status, summary = self._content.update(row, style)

        single_row_updated = False
        if isinstance(status, int):
            height = self._stream.height
            n_visible = min(
                height - last_summary_len - 1,  # -1 for current line.
                self._last_content_len)

            n_back = self._last_content_len - status
            if n_back > n_visible:
                lgr.debug("Cannot move back %d rows for update; "
                          "only %d visible rows",
                          n_back, n_visible)
                status = "repaint"
                content = six.text_type(self._content)
            else:
                lgr.debug("Overwriting line %d with %r", status, row)
                self._stream.overwrite_line(n_back, content)
                single_row_updated = True

        if not single_row_updated:
            if status == "repaint":
                lgr.debug("Repainting the whole thing.  Blame row %r", row)
                self._stream.move_to(self._last_content_len)
            self._stream.write(content)

        if summary is not None:
            self._stream.write(summary)
            lgr.debug("Wrote summary")
        self._last_content_len = len(self._content)
        self._last_summary = summary

    def _write_incremental(self, row, style=None):
        content, status, summary = self._content.update(row, style)
        if isinstance(status, int):
            lgr.debug("Duplicating line %d with %r", status, row)
        elif status == "repaint":
            lgr.debug("Duplicating the whole thing.  Blame row %r", row)
        self._stream.write(content)
        self._last_summary = summary

    def _write_final(self, row, style=None):
        _, _, summary = self._content.update(row, style)
        self._last_summary = summary

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
        """Write styled `row`.

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
            lgr.debug("Inferred columns: %r", self._columns)
        if self._normalizer is None:
            self._init_prewrite()

        callables, row = self._normalizer(row)
        self._write(row, style)
        if callables:
            lgr.debug("Starting callables for row %r", row)
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

    def __getitem__(self, key):
        """Get the (normalized) row for `key`.

        This interface is focused on _writing_ output, and the caller usually
        knows the values.  However, this method can be useful for retrieving
        values that were produced asynchronously (see __call__).

        Parameters
        ----------
        key : tuple
            Unique ID for a row, as specified by the `ids` property.

        Returns
        -------
        A dictionary with the row's current value.
        """
        try:
            return self._content[key]
        except KeyError as exc:
            # Suppress context in py2 compatible way.
            newexc = KeyError(exc)
            newexc.__cause__ = None
            raise newexc
