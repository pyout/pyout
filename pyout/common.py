"""Common components for styled output.

This modules contains things that would be shared across outputters if there
were any besides Tabular.  The Tabular class, though, still contains a good
amount of general logic that should be extracted if any other outputter is
actually added.
"""

from collections import Mapping, Sequence
from functools import partial
import inspect

from pyout.field import Field, Nothing

NOTHING = Nothing()


class RowNormalizer(object):
    """Transform various input data forms to a common form.

    An un-normalized can be one of three kinds:

      * a mapping from column names to keys

      * a sequence of values in the same order as `columns`

      * any other value will be taken as an object where the column values can
        be accessed via an attribute with the same name

    To normalized a row, it is

      * converted to a dict that maps from column names to values

      * all callables are stripped out and replaced with their initial values

      * if the value for a column is missing, it is replaced with a Nothing
        instance whose value is specified by the column's style (an empty
        string by default)

    Parameters
    ----------
    columns : sequence of str
        Column names.
    style : dict, optional
        Column styles.

    Attributes
    ----------
    methods : callable
        A function that takes a row and returns a normalized one.  This is
        chosen at time of the first call.  All subsequent calls should use the
        same kind of row.
    nothings : dict
        Maps column name to the placeholder value to use if that column is
        missing.
    """

    def __init__(self, columns, style):
        self._columns = columns
        self.method = None

        self.nothings = {}  # column => missing value

        for column in columns:
            cstyle = style[column]

            if "missing" in cstyle:
                self.nothings[column] = Nothing(cstyle["missing"])
            else:
                self.nothings[column] = NOTHING

    def __call__(self, row):
        """Normalize `row`

        Parameters
        ----------
        row : mapping, sequence, or other
            Data to normalize.

        Returns
        -------
        A tuple (callables, row), where `callables` is a list (as returned by
        `strip_callables`) and `row` is the normalized row.
        """
        if self.method is None:
            self.method = self._choose_normalizer(row)
        return self.method(row)

    def _choose_normalizer(self, row):
        if isinstance(row, Mapping):
            return partial(self._normalize, self.getter_dict)
        if isinstance(row, Sequence):
            return partial(self._normalize, self.getter_seq)
        return partial(self._normalize, self.getter_attrs)

    def _normalize(self, getter, row):
        if isinstance(row, Mapping):
            callables = self.strip_callables(row)
        else:
            callables = []
        return callables, self._get(getter, row, self._columns)

    @staticmethod
    def _get(getter, row, columns):
        row_norm = {}
        for col in columns:
            row_norm[col] = getter(row, col)
        return row_norm

    @staticmethod
    def strip_callables(row):
        """Extract callable values from `row`.

        Replace the callable values with the initial value (if specified) or
        an empty string.

        Parameters
        ----------
        row : mapping
            A data row.  The keys are either a single column name or a tuple of
            column names.  The values take one of three forms: 1) a
            non-callable value, 2) a tuple (initial_value, callable), 3) or a
            single callable (in which case the initial value is set to an empty
            string).

        Returns
        -------
        list of (column, callable)
        """
        callables = []
        to_delete = []
        to_add = []
        for columns, value in row.items():
            if isinstance(value, tuple):
                initial, fn = value
            else:
                initial = NOTHING
                # Value could be a normal (non-callable) value or a
                # callable with no initial value.
                fn = value

            if callable(fn) or inspect.isgenerator(fn):
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

    # Input-specific getters

    def getter_dict(self, row, column):
        return row.get(column, self.nothings[column])

    def getter_seq(self, row, column):
        col_to_idx = {c: idx for idx, c in enumerate(self._columns)}
        return row[col_to_idx[column]]

    def getter_attrs(self, row, column):
        return getattr(row, column, self.nothings[column])
